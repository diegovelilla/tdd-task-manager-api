import os
from datetime import datetime, timedelta
from typing import cast

from dotenv import find_dotenv, load_dotenv
from jose import jwt
from passlib.context import CryptContext

load_dotenv(find_dotenv())

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_pwd(pwd: str) -> str:
    return pwd_context.hash(pwd)


def verify_pwd(pwd: str, pwd_hash: str) -> bool:
    return pwd_context.verify(pwd, pwd_hash)


def create_token(id: int) -> str:
    exp = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
    secret_key = os.getenv("SECRET_KEY")
    alg = os.getenv("ALGORITHM")
    assert all([exp, secret_key, alg]), "Missing environment variables for token creation"

    # In order to satisfy mypy type checking we should cast these variables
    exp = cast(str, exp)
    secret_key = cast(str, secret_key)
    alg = cast(str, alg)

    expire = datetime.now() + timedelta(minutes=float(exp))
    data = {"sub": str(id), "exp": expire}
    return jwt.encode(data, secret_key, alg)


def decode_token(token: str) -> dict[str, str]:
    secret_key = os.getenv("SECRET_KEY")
    alg = os.getenv("ALGORITHM")
    assert all([secret_key, alg]), "Missing environment variables for token decoding"

    # In order to satisfy mypy type checking we should cast these variables
    secret_key = cast(str, secret_key)
    alg = cast(str, alg)

    payload = jwt.decode(token, secret_key, algorithms=[alg])
    return payload
