# PulseCheck

**Async website uptime & performance monitoring API** built with FastAPI.

Monitor any URL, trigger health checks, track response times, and get uptime statistics — complete with JWT auth, clean architecture, tests, and Docker support.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Why this project?

PulseCheck showcases production-minded Python backend skills:

- FastAPI + Pydantic v2 for typed request/response models
- Async SQLAlchemy 2.0 + SQLite (aiosqlite)
- JWT authentication (register / login / protected routes)
- Service-layer architecture (routers → services → models)
- httpx-based async URL probing with timeout handling
- Pytest suite with dependency overrides & mocked probes
- Docker & docker-compose ready

---

## Features

| Feature | Description |
|---|---|
| User auth | Register, login (OAuth2 password flow), `/me` |
| Monitors | Create / list / update / delete URL monitors |
| Live checks | Trigger an on-demand HTTP probe |
| History | Paginated check results per monitor |
| Stats | Uptime %, avg latency, last status |
| Docs | Interactive Swagger UI at `/docs` |

---

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/EvosROAR/pulsecheck.git
cd pulsecheck

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY`.

### 3. Run the API

```bash
uvicorn app.main:app --reload
```

Open:

- API docs → http://127.0.0.1:8000/docs
- Health check → http://127.0.0.1:8000/health

---

## API overview

### Auth

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

### Monitors

```http
POST   /api/v1/monitors
GET    /api/v1/monitors
GET    /api/v1/monitors/{id}
PATCH  /api/v1/monitors/{id}
DELETE /api/v1/monitors/{id}
POST   /api/v1/monitors/{id}/check
GET    /api/v1/monitors/{id}/checks
GET    /api/v1/monitors/{id}/stats
```

### Example flow

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"you@example.com\",\"full_name\":\"Nuno\",\"password\":\"secret123\"}"

# Login (returns JWT)
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=you@example.com&password=secret123"

# Create a monitor
curl -X POST http://127.0.0.1:8000/api/v1/monitors \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"My Site\",\"url\":\"https://example.com\",\"interval_seconds\":60}"

# Trigger a check
curl -X POST http://127.0.0.1:8000/api/v1/monitors/1/check \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Project structure

```
pulsecheck/
├── app/
│   ├── core/          # config, database, security
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── routers/       # API route handlers
│   ├── services/      # business logic (probe + stats)
│   ├── deps.py        # shared FastAPI dependencies
│   └── main.py        # app factory
├── tests/             # pytest suite
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```

---

## Tests

```bash
pytest -v
```

---

## Docker

```bash
docker compose up --build
```

API available at http://127.0.0.1:8000

---

## Tech stack

- **Python 3.11+**
- **FastAPI** — async web framework
- **SQLAlchemy 2.0** — async ORM
- **Pydantic Settings** — typed configuration
- **python-jose / passlib** — JWT + password hashing
- **httpx** — async HTTP client for probes
- **pytest / pytest-asyncio** — testing
- **Docker** — container deployment

---

## Roadmap ideas

- [ ] Background scheduler for automatic interval checks
- [ ] Webhook / email alerts on downtime
- [ ] PostgreSQL support for production
- [ ] Multi-region probe agents
- [ ] Simple dashboard UI

---

## License

MIT © 2026 Nuno Tamada
