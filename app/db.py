import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  
# пример: mysql+aiomysql://user:pass@localhost:3306/mydb

engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True,)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
