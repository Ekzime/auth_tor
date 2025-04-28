import os
import httpx
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("UTIP_API_KEY")

# http://edge.webtrader.ink/
async def register(data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_BASE}/register", json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    
async def login_user(data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"",json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    
async def reset_password(data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"",json=data, timeout=10)
        r.raise_for_status()
        return r.json()