from typing import Annotated
from fastapi import Depends, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token
from app.db.session import AsyncSessionFactory
from app.modules.auth.repository import UserAccRepository
from app.db.models import UserAcc


# ── Database session ──────────────────────────────────────────

async def get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Auth helpers ──────────────────────────────────────────────

def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException("Missing or malformed Authorization header")
    return token


async def get_current_user(
    request: Request,
    db: DBSession,
) -> UserAcc:
    token = _extract_bearer(request)
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        user_id: str = payload["sub"]
    except (JWTError, KeyError):
        raise UnauthorizedException("Could not validate credentials")

    repo = UserAccRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("Inactive account")
    return user


CurrentUser = Annotated[UserAcc, Depends(get_current_user)]
