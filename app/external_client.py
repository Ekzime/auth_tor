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

    проверяет уникальность email и возвращает ответ от внешнего сервера.
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
    """
    POST BASE_UTIP_URL/RegisterUser — создаёт учётку.
    Возвращает весь JSON-ответ от сервиса.
    """
    kr = _make_key()
    payload = {
        **kr,
        "login":           data["email"],
        "password":        data["password"],
        "password_repeat": data["password_repeat"],
        "first_name":      data["first_name"],
        "second_name":     data["last_name"],
        "email":           data["email"],
    }
    url = f"{BASE_UTIP_URL}/RegisterUser"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

        
async def authentication(data: Dict[str, str]) -> Dict[str, Any]:
    """
    POST /Login?key=…&rand_param=…&user_email=…&password=…
    """
    kr = _make_key()
    payload = {
        **kr,
        "user_email": data["email"],
        "password":   data["password"],
    }
    url = f"{BASE_UTIP_URL}/Login"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

async def generate_recovery_password_letter(email:str):
    """
    POST /GenerateRecoveryPasswordLetter

    Отправляет запрос на сброс пароля на сервер ютипа.
    """
    kr = _make_key()
    data = {
        **kr,
        "user_email": email,
    }
    print(data)
    url = f"{BASE_UTIP_URL}/ForgotYourPassword"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.post(url, data=data, timeout=5)
        resp.raise_for_status()
        return resp.json()