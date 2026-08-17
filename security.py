import os

import jwt
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

pwd_context= CryptContext(
    schemes= ["bcrypt"],
    deprecated= "auto"
)

SECRET_KEY= os.getenv("JWT_SECRET_KEY")
ALGORITHM= "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash:str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(data: dict) -> str:
    return jwt.encode(data, SECRET_KEY, algorithm= ALGORITHM)

def verify_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )