# other libs
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from sqlalchemy import select
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

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(reg: RegisterRequest,db: AsyncSession = Depends(get_db)):
    """
    POST if succes status HTTP-201-CREATED

    Принимает данные, есди чего-то нет из ожидаемого, возвращает ошибку.
    В случае успеха, сохраняет в БД, и отправляет данные на внешний АПИ без номера телефона.
    Ожидает ответ от внешнего АПИ, что бы передать на форму с UI.

    param: reg: RegisterRequest
    param: db: AsyncSession
    """
    # 1) проверяем email во внешнем API
    try:
        uniq = await email_unique(reg.email)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Error checking uniqueness: {e}")
    if uniq.get("result") != "success":
        raise HTTPException(400, detail=uniq.get("description", "Email not unique"))

    # 2) регистрируем во внешнем API
    payload = reg.dict(exclude={"phone"})
    try:
        ext = await register_user(payload)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Error registering externally: {e}")

    # 4) сохраняем в своей БД
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
            raise HTTPException(400, "Phone number already exist")
        raise HTTPException(400, "Uniqueness violation")

    # 5) всё ок, возвращаем внешний ответ + свой user_id
    # редирект ссылка на форму с логином.
    return {
        "status": "success",
        "data": {
            "redirect_url": REDIRECT_URL_TO_LOGIN_FORM
        }
    }


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_endpoint(req: LoginRequest):
    """
    POST login
    Авторизует и возвращает ссылку с автологином на основной сайт.
    """
    # логиним пользователя у партнеров
    try:
        result = await authentication({
            "email":    req.email,
            "password": req.password,
        })
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Error logging in: {e}")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Network error: {e}")

    if result.get("result") != "success":
        raise HTTPException(
            status_code=400,
            detail={
                "description":  result.get("description"),
                "errors":       result.get("errors", {}),
                "error_number": result.get("error_number")
            }
        )
    # формируем ссылку для редиректа с автологином.
    auth_token = result['values']['auth_token']
    redirect_url = f'{BASE_REDIRECT_URL}/{auth_token}/{req.email}/{req.language}'
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

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )