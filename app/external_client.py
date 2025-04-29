from dotenv import load_dotenv
from typing import Dict, Any
import hashlib
import random
import httpx
import os

load_dotenv()
UTIP_API_KEY = os.getenv("UTIP_API_KEY")
BASE_UTIP_URL = os.getenv("BASE_UTIP_URL")

def _make_key() -> Dict[str,str]:
    rand_param = str(random.randint(1_000_000, 99_999_999))
    key = hashlib.md5(f"{UTIP_API_KEY}{rand_param}".encode()).hexdigest()
    return {"key": key, "rand_param": rand_param}

async def email_unique(email: str) -> Dict[str, Any]:
    """
    GET BASE_UTIP_URL/EmailUnique?key=…&rand_param=…&email=…
    """
    kr = _make_key()
    params = {**kr, "email": email}
    url    = f"{BASE_UTIP_URL}/EmailUnique"  

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # делаем GET, а не POST!
        resp = await client.get(url, params=params, timeout=5)
        resp.raise_for_status()    # бросит HTTPStatusError на 4xx/5xx
        return resp.json()

async def register_user(data: Dict[str, str]) -> Dict[str, Any]:
    '''
    1) POST http://edge.webtrader.ink/RegisterUser
    2) GET  http://edge.webtrader.ink/Activation

    Отправляет данные на сервер ютипа.
    '''
    rand_param = str(random.randint(1_000_000, 99_999_999))
    key = hashlib.md5(f"{UTIP_API_KEY}{rand_param}".encode()).hexdigest()

    # 2) Формируем payload для RegisterUser
    payload = {
        "key": key,
        "rand_param": rand_param,
        "login": data['email'],
        "password": data['password'],
        "password_repeat": data['password_repeat'],
        "first_name": data['first_name'],
        "last_name": data['last_name'],
        "email": data['email'],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(f'{BASE_UTIP_URL}/RegisterUser',data=payload, timeout=10)
        resp.raise_for_status()
        out = resp.json()
    
    if out.get("result") != 'success':
        raise Exception(f"RegisterUser failed: {out}")
    
    # 3) Второй этап — Activation
    vals = out.get("values", {})
    activation_key  = vals.get("activation_key")
    activation_type = vals.get("activation_type")

    params = {
        "key":            key,
        "rand_param":     rand_param,
        "activation_key": activation_key,
        "activation_type":activation_type,
    }

    async with httpx.AsyncClient() as client:
        resp2 = await client.get(f"{BASE_UTIP_URL}/Activation", params=params, timeout=10)
        resp2.raise_for_status()
        activation_out = resp2.json()

    return {
        "register":   out,
        "activation": activation_out,
    }