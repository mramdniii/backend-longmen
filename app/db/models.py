"""
ORM models.

Typos corrected from the original schema spec:
  - permissions.permission_code / permission_name: varhcar → varchar
  - loginLogs.login_type:                          varhcar → varchar
  - userAcc.failed_login_attemps:                  attemps → attempts
  - accLock.failed_attemps:                        attemps → attempts
  - userInvitation.created_at:                     timpestamp → timestamp
"""

import uuid
from datetime import datetime, date

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Reference / lookup tables ─────────────────────────────────

class CountryCode(Base):
    __tablename__ = "country_code"

    id = Column(Integer, primary_key=True)
    country_name = Column(String(100), nullable=False)
    phone_code = Column(String(10), nullable=False)
    iso_code = Column(String(2))
    is_active = Column(Boolean, default=True, server_default=text("true"))
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    user_accounts = relationship("UserAcc", back_populates="country_code_ref")


class ProdGroup(Base):
    __tablename__ = "prod_group"

    id = Column(Integer, primary_key=True)
    group_code = Column(String(20), unique=True, nullable=False)
    group_name = Column(String(50), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, server_default=text("true"))
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    products = relationship("ProdList", back_populates="prod_group")


class ProdList(Base):
    __tablename__ = "prod_list"

    id = Column(Integer, primary_key=True)
    prod_group_id = Column(Integer, ForeignKey("prod_group.id"), nullable=False)
    product_code = Column(String(20), unique=True, nullable=False)
    product_name = Column(String(100), nullable=False)
    price_monthly = Column(Numeric(15, 2))
    price_yearly = Column(Numeric(15, 2))
    max_users = Column(Integer)
    max_ponds = Column(Integer)
    features = Column(JSONB)
    is_active = Column(Boolean, default=True, server_default=text("true"))
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    prod_group = relationship("ProdGroup", back_populates="products")
    user_versions = relationship("UserVersion", back_populates="prod_list")


class Version(Base):
    __tablename__ = "version"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    version_code = Column(String(20), unique=True, nullable=False)
    version_name = Column(String(100))
    release_note = Column(Text)
    release_date = Column(DateTime)
    is_active = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())


# ── RBAC ──────────────────────────────────────────────────────

class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True)
    role_code = Column(String(50), unique=True, nullable=False)
    role_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_system_role = Column(Boolean, default=False, server_default=text("false"))
    is_active = Column(Boolean, default=True, server_default=text("true"))
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    role_permissions = relationship("RolePermission", back_populates="role")
    account_roles = relationship("AccRole", back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    # typo fix: varhcar → varchar
    permission_code = Column(String(100), unique=True, nullable=False)
    permission_name = Column(String(100), nullable=False)
    module = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    role_permissions = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    is_allowed = Column(Boolean, default=True, server_default=text("true"))
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"))

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


# ── User account (core auth table) ───────────────────────────

class UserAcc(Base):
    __tablename__ = "user_acc"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    country_code_id = Column(Integer, ForeignKey("country_code.id"))
    phone_number = Column(String(20))
    is_email_verified = Column(Boolean, default=False, server_default=text("false"))
    is_phone_verified = Column(Boolean, default=False, server_default=text("false"))
    is_active = Column(Boolean, default=True, server_default=text("true"))
    is_locked = Column(Boolean, default=False, server_default=text("false"))
    # typo fix: failed_login_attemps → failed_login_attempts
    failed_login_attempts = Column(
        Integer, default=0, server_default=text("0"),
        name="failed_login_attempts"
    )
    locked_until = Column(DateTime)
    last_login = Column(DateTime)
    last_activity = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    country_code_ref = relationship("CountryCode", back_populates="user_accounts")
    user_info = relationship("UserInfo", back_populates="user_acc", uselist=False)
    account_roles = relationship("AccRole", foreign_keys="[AccRole.user_acc_id]", back_populates="user_acc")
    login_logs = relationship("LoginLog", back_populates="user_acc")
    password_resets = relationship("PasswordReset", back_populates="user_acc")
    password_history = relationship("PasswordHistory", foreign_keys="[PasswordHistory.user_acc_id]", back_populates="user_acc")
    acc_locks = relationship("AccLock", foreign_keys="[AccLock.user_acc_id]", back_populates="user_acc")
    audit_logs = relationship("AuditLog", back_populates="user_acc")
    user_versions = relationship("UserVersion", back_populates="user_acc")
    billings = relationship("UserBilling", back_populates="user_acc")
    bank_accounts = relationship("UserBankAcc", back_populates="user_acc")


class AccRole(Base):
    __tablename__ = "acc_roles"
    __table_args__ = (UniqueConstraint("user_acc_id", name="uq_acc_roles_user_acc"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"))
    assigned_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    notes = Column(Text)
    is_active = Column(Boolean, default=True, server_default=text("true"))

    user_acc = relationship("UserAcc", foreign_keys=[user_acc_id], back_populates="account_roles")
    role = relationship("Role", back_populates="account_roles")


# ── User profile / billing / banking ─────────────────────────

class UserInfo(Base):
    __tablename__ = "user_info"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    company_name = Column(String(100))
    position = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    province = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(10))
    profile_picture_url = Column(Text)
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    user_acc = relationship("UserAcc", back_populates="user_info")
    changes = relationship("UserInfoChange", back_populates="user_info")


class UserInfoChange(Base):
    __tablename__ = "user_info_change"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_info_id = Column(UUID(as_uuid=True), ForeignKey("user_info.id"), nullable=False)
    change_field = Column(String(50), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"))
    approval_status = Column(String(50), default="pending", server_default=text("'pending'"))
    approval_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    user_info = relationship("UserInfo", back_populates="changes")


class UserVersion(Base):
    __tablename__ = "user_version"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    version_id = Column(Integer, nullable=False)
    prod_list_id = Column(Integer, ForeignKey("prod_list.id"), nullable=False)
    subscription_start = Column(Date, nullable=False)
    subscription_end = Column(Date)
    subscription_status = Column(String(20), default="active", server_default=text("'active'"))
    payment_status = Column(String(20))
    version_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    user_acc = relationship("UserAcc", back_populates="user_versions")
    prod_list = relationship("ProdList", back_populates="user_versions")


class UserBilling(Base):
    __tablename__ = "user_billing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    billing_name = Column(String(100), nullable=False)
    billing_address = Column(Text, nullable=False)
    billing_city = Column(String(100))
    billing_province = Column(String(100))
    billing_country = Column(String(100))
    billing_postal_code = Column(String(10))
    tax_id = Column(String(50))
    email_invoice = Column(String(100))
    phone_invoice = Column(String(20))
    payment_method = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    user_acc = relationship("UserAcc", back_populates="billings")


class UserBankAcc(Base):
    __tablename__ = "user_bank_acc"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    bank_name = Column(String(100), nullable=False)
    bank_branch = Column(String(100))
    account_number = Column(String(100), nullable=False)
    account_name = Column(String(100), nullable=False)
    currency = Column(String(20), default="idr", server_default=text("'idr'"))
    swift_code = Column(String(20))
    is_default = Column(Boolean, default=False, server_default=text("false"))
    is_active = Column(Boolean, default=True, server_default=text("true"))
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    user_acc = relationship("UserAcc", back_populates="bank_accounts")


# ── Auth / security tables ────────────────────────────────────

class AccLock(Base):
    __tablename__ = "acc_lock"
    __table_args__ = (
        Index("ix_acc_lock_user_acc_id", "user_acc_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    lock_reason = Column(String(100))
    # typo fix: failed_attemps → failed_attempts
    failed_attempts = Column(Integer, default=0, server_default=text("0"), name="failed_attempts")
    locked_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    locked_until = Column(DateTime)
    unlocked_at = Column(DateTime)
    unlocked_by = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"))
    ip_address = Column(INET)

    user_acc = relationship("UserAcc", foreign_keys="[AccLock.user_acc_id]", back_populates="acc_locks")


class LoginLog(Base):
    __tablename__ = "login_logs"
    __table_args__ = (
        Index("ix_login_logs_user_acc_id", "user_acc_id"),
        Index("ix_login_logs_created_at", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"))
    # typo fix: varhcar → varchar
    login_type = Column(String(20))
    login_status = Column(String(20))
    ip_address = Column(INET)
    device_info = Column(Text)
    location = Column(String(255))
    failed_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    user_acc = relationship("UserAcc", back_populates="login_logs")


class PasswordHistory(Base):
    __tablename__ = "password_history"
    __table_args__ = (
        Index("ix_password_history_user_acc_id", "user_acc_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    password_hash = Column(String(255), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    changed_by = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"))
    ip_address = Column(INET)

    user_acc = relationship("UserAcc", foreign_keys="[PasswordHistory.user_acc_id]", back_populates="password_history")


class PasswordReset(Base):
    __tablename__ = "password_reset"
    __table_args__ = (
        Index("ix_password_reset_token", "token"),
        Index("ix_password_reset_user_acc_id", "user_acc_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    token_type = Column(String(20), default="PASSWORD_RESET", server_default=text("'PASSWORD_RESET'"))
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    created_ip = Column(INET)

    user_acc = relationship("UserAcc", back_populates="password_resets")


# ── Audit / invitation ────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_acc_id", "user_acc_id"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_acc_id = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(100))
    old_data = Column(JSONB)
    new_data = Column(JSONB)
    ip_address = Column(INET)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    user_acc = relationship("UserAcc", back_populates="audit_logs")


class UserInvitation(Base):
    __tablename__ = "user_invitation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("user_acc.id"), nullable=False)
    invitee_email = Column(String(100), nullable=False)
    invitee_name = Column(String(100))
    role_id = Column(Integer, ForeignKey("role.id"))
    farm_id = Column(UUID(as_uuid=True))
    pond_group_id = Column(UUID(as_uuid=True))
    pond_id = Column(UUID(as_uuid=True))
    prod_group_id = Column(Integer, ForeignKey("prod_group.id"))
    prod_list_id = Column(Integer, ForeignKey("prod_list.id"))
    additional_permission = Column(JSONB)
    token = Column(String(255), unique=True, nullable=False)
    # typo fix: timpestamp → timestamp
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    status = Column(String(20), default="pending", server_default=text("'pending'"))
    notes = Column(Text)
