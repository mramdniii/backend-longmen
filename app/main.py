from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.auth.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connection pool is created lazily by SQLAlchemy
    yield
    # Shutdown: dispose engine
    from app.db.session import engine
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)


# ── Global exception handler ──────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# ── Routers ───────────────────────────────────────────────────

app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "env": settings.APP_ENV}
