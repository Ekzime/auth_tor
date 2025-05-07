# app/test_async.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "mysql+asyncmy://www-root:Aa123456789%25@45.84.0.220:1501/clients"

async def test_connection():
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,
        pool_pre_ping=True,
        pool_recycle=3600,  
    )
    try:
        async with engine.connect() as conn:
            result = await conn.execute("SELECT DATABASE();")
            db = result.scalar()
            print("✅ Async подключение успешно! БД:", db)
    except Exception as e:
        print("‼️ Async ошибка подключения:", e)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
