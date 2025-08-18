import os
from typing import AsyncIterator

from beanie import Document, init_beanie
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy
from fastapi_users.db import BeanieUserDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr


class User(Document):
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False

    class Settings:
        name = "users"


class UserRead(BaseModel):
    id: str
    email: EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


async def get_user_db() -> AsyncIterator[BeanieUserDatabase[User]]:
    client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    await init_beanie(client[os.getenv("MONGO_DB", "stockdb")], document_models=[User])
    yield BeanieUserDatabase(User)


def get_jwt_strategy() -> JWTStrategy:
    secret = os.getenv("AUTH_SECRET", "CHANGE_ME")
    return JWTStrategy(secret=secret, lifetime_seconds=3600)


cookie_transport = CookieTransport(cookie_name="auth", cookie_max_age=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


fastapi_users = FastAPIUsers[User, str](get_user_db, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
