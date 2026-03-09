# Auth Module — FastAPI + PostgreSQL

Production-ready authentication module using **FastAPI**, **SQLAlchemy 2 (async)**, **Alembic**, and **JWT**.

---

## Architecture

```
app/
├── main.py                        # FastAPI app factory & router registration
├── core/
│   ├── config.py                  # Pydantic-settings (reads .env)
│   ├── security.py                # JWT encode/decode, bcrypt hashing
│   ├── exceptions.py              # Typed HTTP exceptions
│   └── dependencies.py            # FastAPI Depends: DB session, current user
├── db/
│   ├── session.py                 # Async engine + session factory
│   ├── models.py                  # SQLAlchemy ORM (all tables)
│   └── migrations/
│       ├── env.py                 # Alembic async env
│       └── versions/              # Migration files (auto-generated)
└── modules/
    └── auth/
        ├── schema.py              # Pydantic request / response models
        ├── repository.py          # Data access layer (DB only)
        ├── service.py             # Business logic
        └── router.py              # HTTP endpoints
```

---

## Features

| Feature | Details |
|---|---|
| Email + Password login | bcrypt hash verification |
| Account lock | Locked after **3** failed attempts (configurable), auto-unlocks after 30 min |
| Login logs | Every attempt (success or failure) written to `login_logs` |
| Password reset | Secure random token stored in `password_reset`, expires in 60 min |
| Password history | Last 5 passwords stored; reuse rejected |
| Multi-tenant | `tenant_id` embedded in JWT `access_token` claims |
| Audit trail | Key actions written to `audit_logs` |
| JWT | Short-lived access token + long-lived refresh token |

---

## Typos Corrected (vs original schema)

| Table | Column | Original | Fixed |
|---|---|---|---|
| `permissions` | `permission_code`, `permission_name` | `varhcar` | `varchar` |
| `login_logs` | `login_type` | `varhcar` | `varchar` |
| `user_acc` | `failed_login_attempts` | `failed_login_attemps` | `failed_login_attempts` |
| `acc_lock` | `failed_attempts` | `failed_attemps` | `failed_attempts` |
| `user_invitation` | `created_at` | `timpestamp` | `timestamp` |

---

## Quick Start

```bash
# 1. Clone / copy files
cp .env.example .env
# Edit .env with your DB credentials and a strong SECRET_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Start the server
uvicorn app.main:app --reload
```

API docs → http://localhost:8000/docs

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | `postgresql+asyncpg://...` |
| `SECRET_KEY` | — | Long random string |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `MAX_FAILED_LOGIN_ATTEMPTS` | `3` | Before account lock |
| `ACCOUNT_LOCK_DURATION_MINUTES` | `30` | Lock duration |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | `60` | Reset token TTL |

---

## API Endpoints

### Public

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new account |
| `POST` | `/api/v1/auth/login` | Email + password login |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `POST` | `/api/v1/auth/password-reset/request` | Request reset email |
| `POST` | `/api/v1/auth/password-reset/confirm` | Confirm reset with token |

### Protected (Bearer token required)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/auth/me` | Current user profile |
| `GET` | `/api/v1/auth/me/login-history` | Last 20 login events |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Adding a New Migration

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

---

## Multi-Tenant Usage

Pass `tenant_id` in the login or register payload:

```json
{
  "email": "user@tenant.com",
  "password": "...",
  "tenant_id": "acme-corp"
}
```

The `tenant_id` is embedded in the JWT access token claims and can be read in any downstream service:

```python
payload = decode_token(token)
tenant = payload.get("tenant_id")
```
