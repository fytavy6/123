import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List
 
import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel
 
SECRET_KEY = "rbac-secret-change-me"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60
 
app = FastAPI(title="Task 7.1 — RBAC")
bearer_scheme = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
 
fake_users_db: dict[str, dict] = {}  # username -> {hashed_password, role}
 
 
# ── Roles & permissions ───────────────────────────────────────────────────────
 
class Role(str, Enum):
    admin = "admin"
    user = "user"
    guest = "guest"
 
 
ROLE_PERMISSIONS: dict[Role, List[str]] = {
    Role.admin: ["create", "read", "update", "delete"],
    Role.user:  ["read", "update"],
    Role.guest: ["read"],
}
 
 
# ── Models ────────────────────────────────────────────────────────────────────
 
class RegisterRequest(BaseModel):
    username: str
    password: str
    role: Role = Role.user
 
 
class LoginRequest(BaseModel):
    username: str
    password: str
 
 
class ResourceCreate(BaseModel):
    name: str
    value: str
 
 
class ResourceUpdate(BaseModel):
    name: str | None = None
    value: str | None = None
 
 
# ── In-memory resource store ──────────────────────────────────────────────────
 
resources: dict[int, dict] = {}
_next_id = 1
 
 
# ── JWT helpers ───────────────────────────────────────────────────────────────
 
def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
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
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    return decode_token(creds.credentials)
 
 
def require_permission(permission: str):
    """Dependency factory: проверяет наличие нужного права у пользователя."""
    def checker(user: dict = Depends(get_current_user)):
        role = Role(user.get("role", "guest"))
        if permission not in ROLE_PERMISSIONS.get(role, []):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' lacks permission '{permission}'",
            )
        return user
    return checker
 
 
# ── Auth endpoints ────────────────────────────────────────────────────────────
 
@app.post("/register", status_code=201)
def register(data: RegisterRequest):
    existing = next(
        (u for u in fake_users_db if secrets.compare_digest(u, data.username)), None
    )
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    fake_users_db[data.username] = {
        "hashed_password": pwd_context.hash(data.password),
        "role": data.role,
    }
    return {"message": f"User '{data.username}' registered with role '{data.role}'"}
 
 
@app.post("/login")
def login(data: LoginRequest):
    stored = next(
        (u for u in fake_users_db if secrets.compare_digest(u, data.username)), None
    )
    if not stored or not pwd_context.verify(data.password, fake_users_db[stored]["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(stored, fake_users_db[stored]["role"])
    return {"access_token": token, "token_type": "bearer"}
 
 
# ── Protected resource (admin + user) ────────────────────────────────────────
 
@app.get("/protected_resource")
def protected_resource(user: dict = Depends(require_permission("read"))):
    return {
        "message": f"Welcome, {user['sub']}!",
        "role": user["role"],
        "permissions": ROLE_PERMISSIONS[Role(user["role"])],
    }
 
 
# ── CRUD endpoints ────────────────────────────────────────────────────────────
 
@app.post("/resources", status_code=201)
def create_resource(
    body: ResourceCreate,
    user: dict = Depends(require_permission("create")),
):
    global _next_id
    rid = _next_id
    _next_id += 1
    resources[rid] = {"id": rid, "name": body.name, "value": body.value, "owner": user["sub"]}
    return resources[rid]
 
 
@app.get("/resources/{rid}")
def read_resource(rid: int, user: dict = Depends(require_permission("read"))):
    item = resources.get(rid)
    if not item:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item
 
 
@app.put("/resources/{rid}")
def update_resource(
    rid: int,
    body: ResourceUpdate,
    user: dict = Depends(require_permission("update")),
):
    item = resources.get(rid)
    if not item:
        raise HTTPException(status_code=404, detail="Resource not found")
    if body.name is not None:
        item["name"] = body.name
    if body.value is not None:
        item["value"] = body.value
    return item
 
 
@app.delete("/resources/{rid}")
def delete_resource(rid: int, user: dict = Depends(require_permission("delete"))):
    if rid not in resources:
        raise HTTPException(status_code=404, detail="Resource not found")
    del resources[rid]
    return {"message": f"Resource {rid} deleted"}