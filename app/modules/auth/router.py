"""
Auth Router

All /auth endpoints. Thin layer: validates input, calls service, returns response.
"""

from fastapi import APIRouter, Request

from app.core.dependencies import CurrentUser, DBSession
from app.modules.auth.schema import (
    LoginLogResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserAccResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _ip(request: Request) -> str | None:
    """Extract real client IP, handling reverse-proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _device(request: Request) -> str | None:
    return request.headers.get("User-Agent")


# ── Public endpoints ──────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Register a new user account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: DBSession,
) -> TokenResponse:
    svc = AuthService(db)
    return await svc.register(payload, ip_address=_ip(request))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email + password",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: DBSession,
) -> TokenResponse:
    svc = AuthService(db)
    return await svc.login(
        payload,
        ip_address=_ip(request),
        device_info=_device(request),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new token pair",
)
async def refresh(
    payload: RefreshRequest,
    db: DBSession,
) -> TokenResponse:
    svc = AuthService(db)
    return await svc.refresh_token(payload.refresh_token)


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    summary="Request a password-reset email",
)
async def password_reset_request(
    payload: PasswordResetRequestSchema,
    request: Request,
    db: DBSession,
) -> MessageResponse:
    svc = AuthService(db)
    result = await svc.request_password_reset(payload, ip_address=_ip(request))
    return MessageResponse(**result)


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Confirm password reset using token",
)
async def password_reset_confirm(
    payload: PasswordResetConfirmSchema,
    request: Request,
    db: DBSession,
) -> MessageResponse:
    svc = AuthService(db)
    result = await svc.confirm_password_reset(payload, ip_address=_ip(request))
    return MessageResponse(**result)


# ── Protected endpoints ───────────────────────────────────────

@router.get(
    "/me",
    response_model=UserAccResponse,
    summary="Get current authenticated user",
)
async def me(current_user: CurrentUser) -> UserAccResponse:
    return UserAccResponse.model_validate(current_user)


@router.get(
    "/me/login-history",
    response_model=list[LoginLogResponse],
    summary="Get login history for current user",
)
async def login_history(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = 20,
) -> list[LoginLogResponse]:
    svc = AuthService(db)
    logs = await svc.get_login_history(current_user.id, limit=limit)
    return [LoginLogResponse.model_validate(log) for log in logs]
