import uuid

from fastapi import Cookie, Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.domain.auth import load_user_with_relations
from app.models import User


def get_current_user(
    access_token: str | None = Cookie(default=None, alias=settings.cookie_name),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, settings.jwt_secret, algorithms=["HS256"])
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Not authenticated") from None

    user = load_user_with_relations(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
