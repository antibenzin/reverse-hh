from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory stub until DB layer is implemented (Foundation epic)
_users_db: dict[str, dict] = {}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    is_admin: bool = False
    has_candidate_profile: bool = False


def _create_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret,
        algorithm="HS256",
    )


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_expire_hours * 3600,
    )


@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response):
    if body.email in _users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(len(_users_db) + 1)
    _users_db[body.email] = {
        "id": user_id,
        "email": body.email,
        "password_hash": pwd_context.hash(body.password),
        "display_name": body.display_name,
    }
    token = _create_token(user_id)
    _set_auth_cookie(response, token)
    return {"id": user_id}


@router.post("/login")
def login(body: LoginRequest, response: Response):
    user = _users_db.get(body.email)
    if not user or not pwd_context.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_token(user["id"])
    _set_auth_cookie(response, token)
    return {"ok": True}


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(settings.cookie_name)
    return None


@router.get("/me", response_model=UserResponse)
def me():
    # Stub: returns 401 until cookie parsing dependency is added in Foundation epic
    raise HTTPException(status_code=401, detail="Not authenticated")
