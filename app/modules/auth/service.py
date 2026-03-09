"""
Auth Service

Business logic layer. Orchestrates repositories, enforces rules:
  - 3-strike account lock
  - Password history check
  - Multi-tenant token claims
  - Login log writes
  - Audit trail
"""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountLockedException,
    BadRequestException,
    ConflictException,
    InvalidTokenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.repository import (
    AccLockRepository,
    AuditLogRepository,
    LoginLogRepository,
    PasswordHistoryRepository,
    PasswordResetRepository,
    UserAccRepository,
    UserInfoRepository,
)
from app.modules.auth.schema import (
    LoginRequest,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RegisterRequest,
    TokenResponse,
)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._users = UserAccRepository(db)
        self._user_info = UserInfoRepository(db)
        self._login_logs = LoginLogRepository(db)
        self._acc_locks = AccLockRepository(db)
        self._pw_resets = PasswordResetRepository(db)
        self._pw_history = PasswordHistoryRepository(db)
        self._audit = AuditLogRepository(db)

    # ── Registration ──────────────────────────────────────────

    async def register(
        self,
        payload: RegisterRequest,
        ip_address: str | None = None,
    ) -> TokenResponse:
        if await self._users.get_by_email(payload.email):
            raise ConflictException("Email already registered")
        if await self._users.get_by_username(payload.username):
            raise ConflictException("Username already taken")

        user = await self._users.create(
            username=payload.username.lower(),
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
        )

        await self._user_info.create(
            user_acc_id=user.id,
            full_name=payload.full_name,
        )

        await self._pw_history.create(
            user_acc_id=user.id,
            password_hash=user.password_hash,
            changed_by=user.id,
            ip_address=ip_address,
        )

        await self._audit.create(
            user_acc_id=user.id,
            action="USER_REGISTERED",
            entity_type="user_acc",
            entity_id=str(user.id),
            ip_address=ip_address,
        )

        return TokenResponse(
            access_token=create_access_token(
                str(user.id), tenant_id=payload.tenant_id
            ),
            refresh_token=create_refresh_token(str(user.id)),
        )

    # ── Login ─────────────────────────────────────────────────

    async def login(
        self,
        payload: LoginRequest,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> TokenResponse:
        user = await self._users.get_by_email(payload.email)

        # Unknown email → log attempt without user_acc_id, raise generic error
        if not user:
            await self._login_logs.create(
                login_type="EMAIL_PASSWORD",
                login_status="FAILED",
                ip_address=ip_address,
                device_info=device_info,
                failed_reason="Email not found",
            )
            raise UnauthorizedException("Invalid credentials")

        # ── Check active lock ─────────────────────────────────
        if user.is_locked:
            if user.locked_until and user.locked_until > datetime.utcnow():
                await self._login_logs.create(
                    user_acc_id=user.id,
                    login_type="EMAIL_PASSWORD",
                    login_status="FAILED",
                    ip_address=ip_address,
                    device_info=device_info,
                    failed_reason="Account locked",
                )
                raise AccountLockedException(
                    f"Account locked until {user.locked_until.isoformat()}"
                )
            # Lock expired — auto-unlock
            await self._users.reset_failed_attempts(user)

        # ── Verify password ───────────────────────────────────
        if not verify_password(payload.password, user.password_hash):
            await self._users.increment_failed_attempts(user)

            # Reload to get the latest counter
            user = await self._users.get_by_id(user.id)  # type: ignore[assignment]
            attempts = user.failed_login_attempts  # type: ignore[union-attr]

            log_reason = f"Wrong password (attempt {attempts})"

            if attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                locked_until = datetime.utcnow() + timedelta(
                    minutes=settings.ACCOUNT_LOCK_DURATION_MINUTES
                )
                await self._users.lock_account(user, locked_until)
                await self._acc_locks.create(
                    user_acc_id=user.id,
                    lock_reason="Too many failed login attempts",
                    failed_attempts=attempts,
                    locked_until=locked_until,
                    ip_address=ip_address,
                )
                log_reason = "Account locked after max failed attempts"

            await self._login_logs.create(
                user_acc_id=user.id,
                login_type="EMAIL_PASSWORD",
                login_status="FAILED",
                ip_address=ip_address,
                device_info=device_info,
                failed_reason=log_reason,
            )

            if attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                raise AccountLockedException("Too many failed attempts. Account locked.")
            raise UnauthorizedException("Invalid credentials")

        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        # ── Success ───────────────────────────────────────────
        await self._users.reset_failed_attempts(user)
        await self._login_logs.create(
            user_acc_id=user.id,
            login_type="EMAIL_PASSWORD",
            login_status="SUCCESS",
            ip_address=ip_address,
            device_info=device_info,
        )
        await self._audit.create(
            user_acc_id=user.id,
            action="USER_LOGIN",
            entity_type="user_acc",
            entity_id=str(user.id),
            ip_address=ip_address,
        )

        return TokenResponse(
            access_token=create_access_token(
                str(user.id), tenant_id=payload.tenant_id
            ),
            refresh_token=create_refresh_token(str(user.id)),
        )

    # ── Token refresh ─────────────────────────────────────────

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        from jose import JWTError

        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise InvalidTokenException("Not a refresh token")
            user_id: str = payload["sub"]
        except (JWTError, KeyError):
            raise InvalidTokenException("Invalid or expired refresh token")

        user = await self._users.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )

    # ── Password reset ────────────────────────────────────────

    async def request_password_reset(
        self,
        payload: PasswordResetRequestSchema,
        ip_address: str | None = None,
    ) -> dict:
        user = await self._users.get_by_email(payload.email)
        # Always return a generic message to prevent user enumeration
        if not user:
            return {"message": "If the email exists, a reset link has been sent"}

        # Invalidate any previous pending tokens
        await self._pw_resets.invalidate_previous_tokens(user.id)

        token = secrets.token_urlsafe(48)
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )

        await self._pw_resets.create(
            user_acc_id=user.id,
            token=token,
            expires_at=expires_at,
            created_ip=ip_address,
        )

        await self._audit.create(
            user_acc_id=user.id,
            action="PASSWORD_RESET_REQUESTED",
            entity_type="user_acc",
            entity_id=str(user.id),
            ip_address=ip_address,
        )

        # In production: send `token` via email here
        # e.g. await email_service.send_reset_email(user.email, token)
        return {
            "message": "If the email exists, a reset link has been sent",
            # Only exposed in dev for testing convenience
            "_dev_token": token if settings.APP_ENV == "development" else None,
        }

    async def confirm_password_reset(
        self,
        payload: PasswordResetConfirmSchema,
        ip_address: str | None = None,
    ) -> dict:
        reset = await self._pw_resets.get_valid_token(payload.token)
        if not reset:
            raise InvalidTokenException("Token is invalid or has expired")

        user = await self._users.get_by_id(reset.user_acc_id)
        if not user:
            raise NotFoundException("User not found")

        # Prevent password reuse (last 5)
        recent_hashes = await self._pw_history.get_recent_hashes(user.id, limit=5)
        for old_hash in recent_hashes:
            if verify_password(payload.new_password, old_hash):
                raise BadRequestException(
                    "New password must not match any of the last 5 passwords"
                )

        new_hash = hash_password(payload.new_password)
        await self._users.update_password(user, new_hash)
        await self._pw_resets.mark_used(reset)

        await self._pw_history.create(
            user_acc_id=user.id,
            password_hash=new_hash,
            changed_by=user.id,
            ip_address=ip_address,
        )

        await self._audit.create(
            user_acc_id=user.id,
            action="PASSWORD_RESET_COMPLETED",
            entity_type="user_acc",
            entity_id=str(user.id),
            ip_address=ip_address,
        )

        return {"message": "Password has been reset successfully"}

    # ── Login history ─────────────────────────────────────────

    async def get_login_history(self, user_id: UUID, limit: int = 20) -> list:
        return await self._login_logs.get_recent_by_user(user_id, limit=limit)
