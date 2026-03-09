"""
Auth Repository

All database access for the auth module lives here.
No business logic — pure data access.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AccLock,
    AuditLog,
    LoginLog,
    PasswordHistory,
    PasswordReset,
    UserAcc,
    UserInfo,
)


class UserAccRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: str | UUID) -> UserAcc | None:
        result = await self._db.execute(
            select(UserAcc).where(UserAcc.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserAcc | None:
        result = await self._db.execute(
            select(UserAcc).where(UserAcc.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> UserAcc | None:
        result = await self._db.execute(
            select(UserAcc).where(UserAcc.username == username.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> UserAcc:
        user = UserAcc(**kwargs)
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def increment_failed_attempts(self, user: UserAcc) -> None:
        await self._db.execute(
            update(UserAcc)
            .where(UserAcc.id == user.id)
            .values(
                failed_login_attempts=UserAcc.failed_login_attempts + 1,
                updated_at=datetime.utcnow(),
            )
        )

    async def lock_account(self, user: UserAcc, locked_until: datetime) -> None:
        await self._db.execute(
            update(UserAcc)
            .where(UserAcc.id == user.id)
            .values(
                is_locked=True,
                locked_until=locked_until,
                updated_at=datetime.utcnow(),
            )
        )

    async def reset_failed_attempts(self, user: UserAcc) -> None:
        await self._db.execute(
            update(UserAcc)
            .where(UserAcc.id == user.id)
            .values(
                failed_login_attempts=0,
                is_locked=False,
                locked_until=None,
                last_login=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    async def update_last_login(self, user: UserAcc) -> None:
        await self._db.execute(
            update(UserAcc)
            .where(UserAcc.id == user.id)
            .values(
                last_login=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    async def update_password(self, user: UserAcc, new_hash: str) -> None:
        await self._db.execute(
            update(UserAcc)
            .where(UserAcc.id == user.id)
            .values(
                password_hash=new_hash,
                updated_at=datetime.utcnow(),
            )
        )


class UserInfoRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **kwargs) -> UserInfo:
        info = UserInfo(**kwargs)
        self._db.add(info)
        await self._db.flush()
        return info


class LoginLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **kwargs) -> LoginLog:
        log = LoginLog(**kwargs)
        self._db.add(log)
        await self._db.flush()
        return log

    async def get_recent_by_user(
        self, user_id: UUID, limit: int = 20
    ) -> list[LoginLog]:
        result = await self._db.execute(
            select(LoginLog)
            .where(LoginLog.user_acc_id == user_id)
            .order_by(LoginLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class AccLockRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **kwargs) -> AccLock:
        lock = AccLock(**kwargs)
        self._db.add(lock)
        await self._db.flush()
        return lock

    async def get_active_lock(self, user_id: UUID) -> AccLock | None:
        now = datetime.utcnow()
        result = await self._db.execute(
            select(AccLock)
            .where(
                AccLock.user_acc_id == user_id,
                AccLock.locked_until > now,
                AccLock.unlocked_at.is_(None),
            )
            .order_by(AccLock.locked_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class PasswordResetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **kwargs) -> PasswordReset:
        reset = PasswordReset(**kwargs)
        self._db.add(reset)
        await self._db.flush()
        return reset

    async def get_valid_token(self, token: str) -> PasswordReset | None:
        now = datetime.utcnow()
        result = await self._db.execute(
            select(PasswordReset).where(
                PasswordReset.token == token,
                PasswordReset.expires_at > now,
                PasswordReset.used_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, reset: PasswordReset) -> None:
        await self._db.execute(
            update(PasswordReset)
            .where(PasswordReset.id == reset.id)
            .values(used_at=datetime.utcnow())
        )

    async def invalidate_previous_tokens(self, user_id: UUID) -> None:
        """Mark all unused tokens for the user as used (one-reset-at-a-time policy)."""
        await self._db.execute(
            update(PasswordReset)
            .where(
                PasswordReset.user_acc_id == user_id,
                PasswordReset.used_at.is_(None),
            )
            .values(used_at=datetime.utcnow())
        )


class PasswordHistoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **kwargs) -> PasswordHistory:
        record = PasswordHistory(**kwargs)
        self._db.add(record)
        await self._db.flush()
        return record

    async def get_recent_hashes(
        self, user_id: UUID, limit: int = 5
    ) -> list[str]:
        result = await self._db.execute(
            select(PasswordHistory.password_hash)
            .where(PasswordHistory.user_acc_id == user_id)
            .order_by(PasswordHistory.changed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class AuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **kwargs) -> AuditLog:
        log = AuditLog(**kwargs)
        self._db.add(log)
        await self._db.flush()
        return log
