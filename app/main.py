# other libs
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from sqlalchemy import select, or_
import uvicorn
import httpx
import os

# my module
from .db import get_db, engine
from .models import User, Base
from .schemas import RegisterRequest, LoginRequest, ResetRequest
from .external_client import register_user, email_unique, authentication, generate_recovery_password_letter

load_dotenv()
REDIRECT_URL_TO_LOGIN_FORM = os.getenv("REDIRECT_URL_TO_LOGIN_FORM")
BASE_REDIRECT_URL = os.getenv('BASE_REDIRECT_URL')
DOMEN_FOR_CORS = os.getenv('DOMEN_FOR_CORS')

router = APIRouter(prefix="/api/v1", tags=['v1'])

# table inits
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Инициализация таблиц
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

@router.get('/health',status_code=200)
async def health():
    return {'status': 'ok'}

async def _auth_and_redirect(email: str, password: str, language: str) -> str:
    """
    Логинит пользователя на партнёрском API и возвращает готовую ссылку для редиректа.
    Бросает HTTPException, если что-то пошло не так.
    """
    try:
        result = await authentication({
            "email":    email,
            "password": password,
        })
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, detail=f"Error logging in: {e}")
    except httpx.RequestError as e:
        raise HTTPException(502, detail=f"Network error: {e}")

    if result.get("result") != "success":
        detail = {
            "description":  result.get("description"),
            "errors":       result.get("errors", {}),
            "error_number": result.get("error_number")
        }
        raise HTTPException(status_code=400, detail=detail)

    token = result["values"]["auth_token"]
    # Собираем URL автологина
    return f"{BASE_REDIRECT_URL}/{token}/{email}/{language}"

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(reg: RegisterRequest,db: AsyncSession = Depends(get_db)):
    """
    POST regisgter

    Принимает данные, есkи чего-то нет из ожидаемого, возвращает ошибку.
    В случае успеха, сохраняет в БД, и отправляет данные на внешний АПИ без номера телефона.
    Ожидает ответ от внешнего АПИ, что бы передать на форму с UI.
    """
    # 0) локальная проверка.
    existing = await db.scalar(
        select(User).where(
            or_(User.email == reg.email, User.phone == reg.phone)
        )
    )
    if existing:
        if existing.email == reg.email:
            raise HTTPException(400, detail="Email already exist")
        else:
            raise HTTPException(400, detail="Phone number alredy exist")
    # 1) Проверяем, что email свободен во внешнем API
    try:
        uniq = await email_unique(reg.email)
    except httpx.HTTPError as e:
        raise HTTPException(502, detail=f"Error checking uniqueness: {e}")
    if uniq.get("result") != "success":
        raise HTTPException(400, detail=uniq.get("description", "Email not unique"))

    # 2) Регистрируем во внешнем API
    try:
        ext = await register_user(reg.dict())
    except httpx.HTTPError as e:
        raise HTTPException(502, detail=f"Error registering externally: {e}")

    if ext.get("result") != "success":
        # внешний API вернул ошибку регистрации
        raise HTTPException(400, detail=ext.get("description", "External registration error"))

    # 3) Сохраняем в локальную БД только если внешний API одобрил
    user = User(
        email=reg.email,
        hashed_password=reg.password,
        first_name=reg.first_name,
        last_name=reg.last_name,
        country=reg.country,
        phone=reg.phone,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as e:
        await db.rollback()
        msg = str(e.orig).lower()
        if "phone" in msg:
            raise HTTPException(400, detail="Phone number already exists")
        if "email" in msg:
            raise HTTPException(400, detail="Email already exists")
        raise HTTPException(400, detail="Uniqueness violation")

    # 4)логин и редирект
    redirect_url = await _auth_and_redirect(
        email=reg.email,
        password=reg.password,
        language="ru",  
    ) 
    # 5) Возвращаем результат внешнего API + наш user_id
    return {
        "status":      "success",
        "data":{
            "user_id":     user.id,
            "description": ext.get("description"),
            "values":      ext.get("values", {}),
            "redirect_url":redirect_url,
        },
    }


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_endpoint(req: LoginRequest):
    """
    POST login

    Авторизует и возвращает ссылку с автологином на основной сайт.
    """
    # логиним пользователя у партнеров
    redirect_url = await _auth_and_redirect(
        email=req.email,
        password=req.password,
        language=req.language,
    )
    return {
        "status": "success",
        "data": {
            "redirect_url": redirect_url
        }
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_pass(req: ResetRequest):
    """
    POST /ForgotYourPassword

    Генерирует новый пароль для пользователя по email.
    """
    # 1) зовём внешний метод, передавая req.user_email
    try:
        result = await generate_recovery_password_letter(req.user_email)
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"External service error: {e}")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Network error: {e}")

    # 2) проверяем результат
    if result.get("result") != "success":
        raise HTTPException(
            400,
            detail={
                "description":  result.get("description"),
                "errors":       result.get("errors", []),
                "error_number": result.get("error_number"),
            }
        )

    # 3) возвращаем унифицированный ответ
    return {
        "status": "success",
        "data": {
            "message": result
        }
    }


#-----------------------------------#
app = FastAPI(
            title='Utip Auth Form',
            lifespan=lifespan
        )
app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origin= ['*'],
    allow_methods=['*'],
    allow_headers=["*"],                
    allow_credentials=True, 
)