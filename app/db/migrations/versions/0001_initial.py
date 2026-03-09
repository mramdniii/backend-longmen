"""Initial migration — create all tables

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── country_code ──────────────────────────────────────────
    op.create_table(
        "country_code",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("country_name", sa.String(100), nullable=False),
        sa.Column("phone_code", sa.String(10), nullable=False),
        sa.Column("iso_code", sa.String(2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # ── prod_group ────────────────────────────────────────────
    op.create_table(
        "prod_group",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("group_code", sa.String(20), nullable=False, unique=True),
        sa.Column("group_name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # ── prod_list ─────────────────────────────────────────────
    op.create_table(
        "prod_list",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("prod_group_id", sa.Integer(), sa.ForeignKey("prod_group.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_code", sa.String(20), nullable=False, unique=True),
        sa.Column("product_name", sa.String(100), nullable=False),
        sa.Column("price_monthly", sa.Numeric(15, 2), nullable=True),
        sa.Column("price_yearly", sa.Numeric(15, 2), nullable=True),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("max_ponds", sa.Integer(), nullable=True),
        sa.Column("features", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_prod_list_prod_group_id", "prod_list", ["prod_group_id"])

    # ── version ───────────────────────────────────────────────
    op.create_table(
        "version",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("version_code", sa.String(20), nullable=False, unique=True),
        sa.Column("version_name", sa.String(100), nullable=True),
        sa.Column("release_note", sa.Text(), nullable=True),
        sa.Column("release_date", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # ── role ──────────────────────────────────────────────────
    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role_code", sa.String(50), nullable=False, unique=True),
        sa.Column("role_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── permissions ───────────────────────────────────────────
    # typo fix: varhcar → varchar
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("permission_code", sa.String(100), nullable=False, unique=True),
        sa.Column("permission_name", sa.String(100), nullable=False),
        sa.Column("module", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # ── user_acc ──────────────────────────────────────────────
    # typo fix: failed_login_attemps → failed_login_attempts
    op.create_table(
        "user_acc",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("country_code_id", sa.Integer(), sa.ForeignKey("country_code.id", ondelete="SET NULL"), nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_phone_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("last_activity", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_acc_email", "user_acc", ["email"])
    op.create_index("ix_user_acc_username", "user_acc", ["username"])

    # ── role_permissions ──────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("role.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])

    # ── acc_roles ─────────────────────────────────────────────
    op.create_table(
        "acc_roles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("role.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_acc_roles_role_id", "acc_roles", ["role_id"])

    # ── user_info ─────────────────────────────────────────────
    op.create_table(
        "user_info",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("company_name", sa.String(100), nullable=True),
        sa.Column("position", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("province", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column("profile_picture_url", sa.Text(), nullable=True),
        sa.Column("emergency_contact_name", sa.String(100), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── user_info_change ──────────────────────────────────────
    op.create_table(
        "user_info_change",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_info_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_info.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_field", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_status", sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("approval_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_info_change_user_info_id", "user_info_change", ["user_info_id"])

    # ── user_version ──────────────────────────────────────────
    op.create_table(
        "user_version",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("prod_list_id", sa.Integer(), sa.ForeignKey("prod_list.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subscription_start", sa.Date(), nullable=False),
        sa.Column("subscription_end", sa.Date(), nullable=True),
        sa.Column("subscription_status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("payment_status", sa.String(20), nullable=True),
        sa.Column("version_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_version_user_acc_id", "user_version", ["user_acc_id"])
    op.create_index("ix_user_version_prod_list_id", "user_version", ["prod_list_id"])

    # ── user_billing ──────────────────────────────────────────
    op.create_table(
        "user_billing",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("billing_name", sa.String(100), nullable=False),
        sa.Column("billing_address", sa.Text(), nullable=False),
        sa.Column("billing_city", sa.String(100), nullable=True),
        sa.Column("billing_province", sa.String(100), nullable=True),
        sa.Column("billing_country", sa.String(100), nullable=True),
        sa.Column("billing_postal_code", sa.String(10), nullable=True),
        sa.Column("tax_id", sa.String(50), nullable=True),
        sa.Column("email_invoice", sa.String(100), nullable=True),
        sa.Column("phone_invoice", sa.String(20), nullable=True),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_billing_user_acc_id", "user_billing", ["user_acc_id"])

    # ── user_bank_acc ─────────────────────────────────────────
    op.create_table(
        "user_bank_acc",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bank_name", sa.String(100), nullable=False),
        sa.Column("bank_branch", sa.String(100), nullable=True),
        sa.Column("account_number", sa.String(100), nullable=False),
        sa.Column("account_name", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(20), nullable=False, server_default=sa.text("'idr'")),
        sa.Column("swift_code", sa.String(20), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_bank_acc_user_acc_id", "user_bank_acc", ["user_acc_id"])

    # ── acc_lock ──────────────────────────────────────────────
    # typo fix: failed_attemps → failed_attempts
    op.create_table(
        "acc_lock",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lock_reason", sa.String(100), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("unlocked_at", sa.DateTime(), nullable=True),
        sa.Column("unlocked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
    )
    op.create_index("ix_acc_lock_user_acc_id", "acc_lock", ["user_acc_id"])

    # ── login_logs ────────────────────────────────────────────
    # typo fix: varhcar → varchar
    op.create_table(
        "login_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="SET NULL"), nullable=True),
        sa.Column("login_type", sa.String(20), nullable=True),
        sa.Column("login_status", sa.String(20), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("device_info", sa.Text(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("failed_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_login_logs_user_acc_id", "login_logs", ["user_acc_id"])
    op.create_index("ix_login_logs_created_at", "login_logs", ["created_at"])

    # ── password_history ──────────────────────────────────────
    op.create_table(
        "password_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
    )
    op.create_index("ix_password_history_user_acc_id", "password_history", ["user_acc_id"])

    # ── password_reset ────────────────────────────────────────
    op.create_table(
        "password_reset",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("token_type", sa.String(20), nullable=False, server_default=sa.text("'PASSWORD_RESET'")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_ip", postgresql.INET(), nullable=True),
    )
    op.create_index("ix_password_reset_token", "password_reset", ["token"])
    op.create_index("ix_password_reset_user_acc_id", "password_reset", ["user_acc_id"])

    # ── audit_logs ────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_acc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="SET NULL"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("old_data", postgresql.JSONB(), nullable=True),
        sa.Column("new_data", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_user_acc_id", "audit_logs", ["user_acc_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── user_invitation ───────────────────────────────────────
    # typo fix: timpestamp → timestamp
    op.create_table(
        "user_invitation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_acc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invitee_email", sa.String(100), nullable=False),
        sa.Column("invitee_name", sa.String(100), nullable=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("role.id", ondelete="SET NULL"), nullable=True),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pond_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pond_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prod_group_id", sa.Integer(), sa.ForeignKey("prod_group.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prod_list_id", sa.Integer(), sa.ForeignKey("prod_list.id", ondelete="SET NULL"), nullable=True),
        sa.Column("additional_permission", postgresql.JSONB(), nullable=True),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_user_invitation_token", "user_invitation", ["token"])
    op.create_index("ix_user_invitation_invited_by", "user_invitation", ["invited_by"])
    op.create_index("ix_user_invitation_invitee_email", "user_invitation", ["invitee_email"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("user_invitation")
    op.drop_table("audit_logs")
    op.drop_table("password_reset")
    op.drop_table("password_history")
    op.drop_table("login_logs")
    op.drop_table("acc_lock")
    op.drop_table("user_bank_acc")
    op.drop_table("user_billing")
    op.drop_table("user_version")
    op.drop_table("user_info_change")
    op.drop_table("user_info")
    op.drop_table("acc_roles")
    op.drop_table("role_permissions")
    op.drop_table("user_acc")
    op.drop_table("permissions")
    op.drop_table("role")
    op.drop_table("version")
    op.drop_table("prod_list")
    op.drop_table("prod_group")
    op.drop_table("country_code")
