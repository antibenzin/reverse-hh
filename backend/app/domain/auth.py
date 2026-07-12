"""Authentication domain logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import CompanyMember, User
from app.models.enums import CompanyMemberRole


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


@dataclass(frozen=True)
class CompanyMembershipInfo:
    company_id: str
    company_name: str
    role: CompanyMemberRole


@dataclass(frozen=True)
class UserInfo:
    id: str
    email: str
    display_name: str
    is_admin: bool
    has_candidate_profile: bool
    companies: list[CompanyMembershipInfo]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.jwt_secret,
        algorithm="HS256",
    )


def register_user(db: Session, *, email: str, password: str) -> User:
    if db.query(User).filter(User.email == email).first():
        raise EmailAlreadyRegisteredError()
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    return user


def load_user_with_relations(db: Session, user_id: uuid.UUID) -> User | None:
    return (
        db.query(User)
        .options(
            joinedload(User.candidate_profile),
            joinedload(User.company_memberships).joinedload(CompanyMember.company),
        )
        .filter(User.id == user_id)
        .first()
    )


def user_to_info(user: User) -> UserInfo:
    profile = user.candidate_profile
    return UserInfo(
        id=str(user.id),
        email=user.email,
        display_name=profile.display_name if profile else "",
        is_admin=user.is_admin,
        has_candidate_profile=profile is not None,
        companies=[
            CompanyMembershipInfo(
                company_id=str(m.company_id),
                company_name=m.company.name,
                role=m.role,
            )
            for m in user.company_memberships
        ],
    )
