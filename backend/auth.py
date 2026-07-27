"""JWT authentication and RBAC for V3. Three roles: PHYSICIAN, NURSE, ADMIN."""
from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

# Demo user store — in production this would be a DB collection.
USERS = {
    "doctor": {"password": "doctor123", "role": "PHYSICIAN", "name": "Dr. Smith"},
    "nurse":  {"password": "nurse123",  "role": "NURSE",     "name": "Nurse Johnson"},
    "admin":  {"password": "admin123",  "role": "ADMIN",     "name": "Admin Davis"},
}


def create_token(username: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "role": role, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload["sub"], "role": payload["role"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_physician(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "PHYSICIAN":
        raise HTTPException(status_code=403, detail="Physician access required")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
