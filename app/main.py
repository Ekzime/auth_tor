# other libs
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
import uvicorn
import httpx


# my dirs
from .db import get_db, engine
from .models import User, Base
from .schemas import RegisterRequest, LoginRequest, ResetRequest
from .external_client import register_user, email_unique

#pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# prefix & route
router = APIRouter(prefix="/api/v1", tags=['v1'])

# table inits
@asynccontextmanager
async def lifespan(app: FastAPI):
    # код, который раньше был в on_event('startup')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

# @router.get("/test-email")
# async def test():
#     email = "testexodus@gmail.com"
#     result = await email_unique(email=email)
#     return result

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
    # 0) Проверяем у внешнего АПИ, свободен ли email
    try:
        login_resp = await email_unique(reg.email)
    except httpx.HTTPStatusError as e:
        # любые 5xx/3xx, которых мы не ожидаем, трактуем как проблему связи
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error checking uniqueness: {e}"
        )
    # 0.1) Если внешний сервис нам вернул не success — возвращаем его описание
    if login_resp.get("result") != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=login_resp.get("description", "Email not unique")
        )

    # 1) Дубль email в своей БД 
    if await db.execute(select(User).where(User.email == reg.email)).scalar_one_or_none():
        raise HTTPException(400, "Email already exist")

    # 2) check password
    if reg.password != reg.password_repeat:
        raise HTTPException(
            status_code=400,
            detail="The passwords do not match"
        )
    
    # 3) save to db
    user = User(
        email=reg.email,
        hashed_password=reg.password,
        first_name= reg.first_name,
        last_name=reg.last_name,
        country=reg.country,
        phone=reg.phone
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        if "phone" in str(e.orig).lower():
            raise HTTPException(400, "Phone number already exist")
        raise HTTPException(400, "Uniqueness violation")
    

    # 4) request to external api
    external_reg = reg.dict(exclude={'phone'})
    try:
        #external_result = await register_user(payload)
        pass
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Error request to external api:{e}'
        )
    return external_reg

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