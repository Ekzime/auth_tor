from pydantic import BaseModel, EmailStr, constr
from typing import Literal

class RegisterRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8) # type: ignore
    password_repeat: constr(min_length=8) # type: ignore
    first_name: constr(min_length=3)  # type: ignore
    last_name: constr(min_length=3) # type: ignore
    country: constr(min_length=3) # type: ignore
    phone: constr(min_length=6) # type: ignore

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    language: Literal["en", "ru"]

class ResetRequest(BaseModel):
    user_email: EmailStr
