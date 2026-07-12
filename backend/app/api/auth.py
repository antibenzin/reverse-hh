
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.auth_cookies import clear_auth_cookie, set_auth_cookie
from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    create_access_token,
    register_user,
    user_to_info,
)
from app.models import User
from app.models.enums import CompanyMemberRole

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CompanyMembershipResponse(BaseModel):
    company_id: str
    company_name: str
    role: CompanyMemberRole


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    is_admin: bool = False
    has_candidate_profile: bool = False
    companies: list[CompanyMembershipResponse] = []


def _to_user_response(user: User) -> UserResponse:
    info = user_to_info(user)
    return UserResponse(
        id=info.id,
        email=info.email,
        display_name=info.display_name,
        is_admin=info.is_admin,
        has_candidate_profile=info.has_candidate_profile,
        companies=[
            CompanyMembershipResponse(
                company_id=c.company_id,
                company_name=c.company_name,
                role=c.role,
            )
            for c in info.companies
        ],
    )


@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user = register_user(db, email=body.email, password=body.password)
    except EmailAlreadyRegisteredError:
        raise HTTPException(status_code=400, detail="Email already registered") from None
    token = create_access_token(user.id)
    set_auth_cookie(response, token)
    return {"id": str(user.id)}


@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, email=body.email, password=body.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid credentials") from None
    token = create_access_token(user.id)
    set_auth_cookie(response, token)
    return {"ok": True}


@router.post("/logout", status_code=204)
def logout(response: Response):
    clear_auth_cookie(response)
    return None


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _to_user_response(user)
