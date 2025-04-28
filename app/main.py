# other libs
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
import uvicorn

# my dirs
from .db import get_db, engine
from .models import User, Base
from .schemas import RegisterRequest, LoginRequest, ResetRequest
from .external_client import register, login_user, reset_password

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# prefix & route
router = APIRouter(prefix="/api/v1", tags=['v1'])

# table inits
@asynccontextmanager
async def lifespan(app: FastAPI):
    # код, который раньше был в on_event('startup')
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
    # check to dublicate
    existing = await db.execute(select(User).where(User.email == reg.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email already used"
        )
    # check password
    if reg.password != reg.password_repeat:
        raise HTTPException(
            status_code=400,
            detail="The passwords do not match"
        )
    
    # save to db
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
    



    # request to external api
    external_reg = reg.dict(exclude={'phone'})
    try:
        #result = await register(reg.dict(exclude={"phone"}))
        pass
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Error request to external api:{e}'
        )
    return external_reg

app = FastAPI(
    title='Utip Auth Form',
    lifespan=lifespan
)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )