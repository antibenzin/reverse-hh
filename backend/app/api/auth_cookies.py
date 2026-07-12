from fastapi import Response

from app.config import settings


def _cookie_flags() -> dict[str, bool | str]:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": not settings.debug,
    }


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.jwt_expire_hours * 3600,
        **_cookie_flags(),
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        **_cookie_flags(),
    )
