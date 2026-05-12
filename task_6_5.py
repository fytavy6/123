"""
Задание 6.5 — JWT + bcrypt + rate limiting (slowapi)
"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ── Setup ─────────────────────────────────────────────────────────────────────

SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Task 6.5 — JWT + Rate Limit")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

fake_users_db: dict[str, str] = {}  # username -> hashed_password


# ── Models ────────────────────────────────────────────────────────────────────

class UserRequest(BaseModel):
    username: str
    password: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/register", status_code=201)
@limiter.limit("1/minute")
def register(request: Request, data: UserRequest):
    # check for existing user (timing-safe)
    existing = next(
        (u for u in fake_users_db if secrets.compare_digest(u, data.username)), None
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="User already exists")
    fake_users_db[data.username] = pwd_context.hash(data.password)
    return {"message": "New user created"}


@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, data: UserRequest):
    stored_username = next(
        (u for u in fake_users_db if secrets.compare_digest(u, data.username)), None
    )
    if stored_username is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not pwd_context.verify(data.password, fake_users_db[stored_username]):
        raise HTTPException(status_code=401, detail="Authorization failed")
    return {"access_token": create_token(stored_username), "token_type": "bearer"}


@app.get("/protected_resource")
def protected(username: str = Depends(get_current_user)):
    return {"message": "Access granted"}