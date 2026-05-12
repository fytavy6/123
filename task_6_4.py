import random
from datetime import datetime, timedelta, timezone
 
import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
 
app = FastAPI(title="Task 6.4 — JWT Auth")
 
SECRET_KEY = "super-secret-key-change-in-prod"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30
 
bearer_scheme = HTTPBearer()
 
 
# ── Stub ──────────────────────────────────────────────────────────────────────
 
def authenticate_user(username: str, password: str) -> bool:
    """Заглушка: случайно возвращает True или False."""
    return random.choice([True, False])
 
 
# ── Models ────────────────────────────────────────────────────────────────────
 
class LoginRequest(BaseModel):
    username: str
    password: str
 
 
# ── JWT helpers ───────────────────────────────────────────────────────────────
 
def create_access_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
 
 
def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
 
 
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    payload = decode_token(credentials.credentials)
    return payload["sub"]
 
 
# ── Routes ────────────────────────────────────────────────────────────────────
 
@app.post("/login")
def login(data: LoginRequest):
    if not authenticate_user(data.username, data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data.username)
    return {"access_token": token}
 
 
@app.get("/protected_resource")
def protected(username: str = Depends(get_current_user)):
    return {"message": f"Access granted for {username}"}