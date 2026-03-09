"""
Unit tests for AuthService.

Uses AsyncMock to isolate the service from real DB.
Run with: pytest tests/ -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.exceptions import (
    AccountLockedException,
    ConflictException,
    InvalidTokenException,
    UnauthorizedException,
)
from app.modules.auth.schema import LoginRequest, RegisterRequest
from app.modules.auth.service import AuthService


def _mock_user(
    *,
    is_active: bool = True,
    is_locked: bool = False,
    locked_until: datetime | None = None,
    failed_login_attempts: int = 0,
    password_hash: str = "$2b$12$placeholder",
) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.is_active = is_active
    user.is_locked = is_locked
    user.locked_until = locked_until
    user.failed_login_attempts = failed_login_attempts
    user.password_hash = password_hash
    return user


@pytest.fixture
def db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def svc(db) -> AuthService:
    return AuthService(db)


# ── Registration ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_conflict_email(svc):
    svc._users.get_by_email = AsyncMock(return_value=_mock_user())
    with pytest.raises(ConflictException, match="Email already registered"):
        await svc.register(
            RegisterRequest(
                username="newuser",
                email="taken@example.com",
                password="Str0ng!Pass",
                full_name="Test User",
            )
        )


@pytest.mark.asyncio
async def test_register_conflict_username(svc):
    svc._users.get_by_email = AsyncMock(return_value=None)
    svc._users.get_by_username = AsyncMock(return_value=_mock_user())
    with pytest.raises(ConflictException, match="Username already taken"):
        await svc.register(
            RegisterRequest(
                username="takenuser",
                email="free@example.com",
                password="Str0ng!Pass",
                full_name="Test User",
            )
        )


@pytest.mark.asyncio
async def test_register_success(svc):
    svc._users.get_by_email = AsyncMock(return_value=None)
    svc._users.get_by_username = AsyncMock(return_value=None)
    new_user = _mock_user()
    svc._users.create = AsyncMock(return_value=new_user)
    svc._user_info.create = AsyncMock()
    svc._pw_history.create = AsyncMock()
    svc._audit.create = AsyncMock()

    result = await svc.register(
        RegisterRequest(
            username="newuser",
            email="new@example.com",
            password="Str0ng!Pass",
            full_name="New User",
        )
    )
    assert result.access_token
    assert result.refresh_token


# ── Login ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_unknown_email(svc):
    svc._users.get_by_email = AsyncMock(return_value=None)
    svc._login_logs.create = AsyncMock()
    with pytest.raises(UnauthorizedException):
        await svc.login(LoginRequest(email="ghost@example.com", password="x"))


@pytest.mark.asyncio
async def test_login_locked_account(svc):
    locked_user = _mock_user(
        is_locked=True,
        locked_until=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    svc._users.get_by_email = AsyncMock(return_value=locked_user)
    svc._login_logs.create = AsyncMock()
    with pytest.raises(AccountLockedException):
        await svc.login(LoginRequest(email="test@example.com", password="x"))


@pytest.mark.asyncio
@patch("app.modules.auth.service.verify_password", return_value=False)
async def test_login_wrong_password_increments(mock_verify, svc):
    user = _mock_user(failed_login_attempts=0)
    svc._users.get_by_email = AsyncMock(return_value=user)
    svc._users.increment_failed_attempts = AsyncMock()
    # Return updated user with attempts=1
    updated = _mock_user(failed_login_attempts=1)
    svc._users.get_by_id = AsyncMock(return_value=updated)
    svc._login_logs.create = AsyncMock()

    with pytest.raises(UnauthorizedException):
        await svc.login(LoginRequest(email="test@example.com", password="wrong"))

    svc._users.increment_failed_attempts.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.modules.auth.service.verify_password", return_value=False)
async def test_login_locks_after_max_attempts(mock_verify, svc):
    user = _mock_user(failed_login_attempts=2)  # 2 previous fails, this is the 3rd
    svc._users.get_by_email = AsyncMock(return_value=user)
    svc._users.increment_failed_attempts = AsyncMock()
    updated = _mock_user(failed_login_attempts=3)
    svc._users.get_by_id = AsyncMock(return_value=updated)
    svc._users.lock_account = AsyncMock()
    svc._acc_locks.create = AsyncMock()
    svc._login_logs.create = AsyncMock()

    with pytest.raises(AccountLockedException):
        await svc.login(LoginRequest(email="test@example.com", password="wrong"))

    svc._users.lock_account.assert_awaited_once()
    svc._acc_locks.create.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.modules.auth.service.verify_password", return_value=True)
async def test_login_success(mock_verify, svc):
    user = _mock_user()
    svc._users.get_by_email = AsyncMock(return_value=user)
    svc._users.reset_failed_attempts = AsyncMock()
    svc._login_logs.create = AsyncMock()
    svc._audit.create = AsyncMock()

    result = await svc.login(LoginRequest(email="test@example.com", password="correct"))
    assert result.access_token
    assert result.token_type == "bearer"


# ── Password reset ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_password_reset_unknown_email_no_leak(svc):
    """Should return generic message even for unknown email (anti-enumeration)."""
    svc._users.get_by_email = AsyncMock(return_value=None)
    from app.modules.auth.schema import PasswordResetRequestSchema
    result = await svc.request_password_reset(
        PasswordResetRequestSchema(email="nobody@example.com")
    )
    assert "reset link" in result["message"]


@pytest.mark.asyncio
async def test_password_reset_invalid_token(svc):
    svc._pw_resets.get_valid_token = AsyncMock(return_value=None)
    from app.modules.auth.schema import PasswordResetConfirmSchema
    with pytest.raises(InvalidTokenException):
        await svc.confirm_password_reset(
            PasswordResetConfirmSchema(
                token="badtoken",
                new_password="NewPass123!",
                confirm_password="NewPass123!",
            )
        )
