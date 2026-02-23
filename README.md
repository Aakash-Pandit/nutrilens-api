## Nutrilens AI API

Nutrilens AI is an API that takes food packaging ingredient information (text or image), runs it through AI models, and returns a human-readable explanation of what is inside along with an opinionated health assessment (e.g. whether the product looks healthy, what to watch out for, etc.).

It is designed to power mobile or web clients that let users quickly scan packaged food before buying or consuming it.

---

## 1. What this project is used for

- **Ingredient understanding**: Turn long, hard-to-read ingredient lists into a short, clear summary.
- **Health assessment**: Flag potentially unhealthy ingredients (e.g. excess sugar, certain additives, trans fats) and highlight healthier aspects (e.g. high fiber, whole grains).
- **Developer-friendly API**: Provide a FastAPI-based backend that can be consumed by mobile apps, web apps, or other services.

High-level capabilities:

- **AI-powered ingredient analysis** using Cohere.
- **Image OCR** for ingredient lists using Tesseract + OpenCV.
- **User accounts & auth** via JWT (and hooks for Google OAuth).
- **Notifications/streaming** using Server-Sent Events (SSE).
- **Task processing** (for heavier workloads) using Celery + Redis.

---

## 2. How it is built

- **FastAPI application** in `application/app.py` exposes HTTP endpoints and handles auth, routing, and health checks.
- **AI layer** in `ai/`:
  - `ai/clients.py` wraps the Cohere client (using `COHERE_API_KEY`).
  - `ai/ingredients_analysis.py` takes raw ingredient text, calls Cohere, and returns a concise explanation + health signal.
- **Ingredients module** in `ingredients/`:
  - `ingredients/apis.py` defines endpoints for uploading images or text, stores uploaded files under `INGREDIENTS_UPLOAD_DIR`, and triggers AI analysis.
  - `ingredients/tasks.py` (used by Celery) can offload longer-running analysis jobs.
- **Notifications module** in `notifications/`:
  - `notifications/apis.py` provides CRUD-style endpoints for listing, fetching, and marking notifications as read.
  - It also exposes a **single SSE streaming endpoint** `GET /notifications/stream/{user_id}` that continuously pushes the **current unread notifications count** (and updates after changes), so clients can keep a live unread badge in sync without polling.
- **Auth module** in `auth/`:
  - `auth/backend.py` implements `JWTAuthBackend` to authenticate requests using a JWT from the `Authorization` header (configured via `JWT_SECRET` and `JWT_ALGORITHM`).
  - `auth/dependencies.py` exposes `require_authenticated_user`, which is applied as a global dependency so almost all routes require auth.
- **Database layer** in `database/db.py`:
  - Builds a SQLAlchemy engine from `DATABASE_URL` and initializes/drops tables.
  - Used by user and ingredient models to persist data.
- **Background processing**:
  - `celery_app.py` configures a Celery app using `CELERY_BROKER_URL` (typically a Redis URL) for both broker and result backend.
  - Tasks in `ingredients.tasks` are discovered and executed by a Celery worker.
- **Entrypoint & server**:
  - `main.py` loads environment variables, imports the FastAPI app, and runs it with Uvicorn on the port specified by `API_PORT` (default `8000`).
  - `compose/Dockerfile` provides a multi-stage container build with Tesseract and other system deps.

Tests under `tests/` cover auth, database, and AI integration logic.

---

## 3. What purpose it serves

- **For end users**: Help them make better food choices by demystifying ingredient lists and surfacing potential health concerns.
- **For client apps**: Act as a backend service for:
  - Barcode/packaging scanner apps.
  - Nutrition coaching tools.
  - Grocery or diet-planning apps that want AI explanations of ingredients.
- **For developers**: A reference implementation of:
  - Combining OCR, AI text models, and traditional APIs.
  - FastAPI + SQLAlchemy + Celery + Redis integration.

---

## 4. Tech stack

- **Language**: Python 3.11

- **Web framework**:
  - FastAPI (`fastapi`)
  - ASGI server: Uvicorn (`uvicorn[standard]`)

- **Data & validation**:
  - Pydantic v2 (`pydantic`)
  - `python-multipart` for file uploads

- **Auth**:
  - JWT with `python-jose`
  - Google OAuth via `google-auth` (prepared for social login integration)

- **Database**:
  - SQLAlchemy 2.x
  - PostgreSQL driver: `psycopg2-binary`

- **AI & OCR**:
  - Cohere (`cohere`) for language understanding and ingredient analysis
  - Tesseract OCR via `pytesseract`
  - Image handling via `Pillow` and `opencv-python`

- **Background jobs & messaging**:
  - Celery with Redis (`celery[redis]`, `redis`)

- **Streaming / notifications**:
  - `sse-starlette` for Server-Sent Events

- **Testing & tooling**:
  - `pytest` for tests
  - Optional dev tooling: `black`, `isort`, etc. (see `requirements.txt`)

---

## 5. Running this project locally

The application is fully **Dockerized**. You are expected to run it locally using **Docker Compose**, which will start:

- the FastAPI app
- a Celery worker
- PostgreSQL (with pgvector)
- Redis

### 5.1. Prerequisites

- **Docker** and **Docker Compose plugin** (i.e. `docker compose` available)
- A `.env` file configured as described below (database, JWT, Cohere, etc.)

You will also need a **Cohere API key** to enable AI analysis.

---

### 5.2. Clone and run with Docker Compose

```bash
git clone <this-repo-url>
cd nutrilens-api

# Build and start all services (API, Celery worker, Postgres, Redis)
docker compose up --build -d

# To follow API logs
docker compose logs -f fast-api
```

---

### 5.3. Environment variables

Create a `.env` file in the project root (same folder as `main.py`) and set at least the following variables:

```env
# --- Core API config ---
API_PORT=8000

# --- Database ---
# Example for PostgreSQL:
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db_name>

# --- Auth / JWT ---
JWT_SECRET=change-this-to-a-long-random-string
# Algorithm defaults to HS256 if not set
JWT_ALGORITHM=HS256

# --- AI provider (Cohere) ---
COHERE_API_KEY=your-cohere-api-key

# --- File uploads ---
# Where ingredient images and related files are stored
INGREDIENTS_UPLOAD_DIR=uploads/ingredients

# --- Celery / Redis ---
CELERY_BROKER_URL=redis://localhost:6379/0
```

Notes:

- `DATABASE_URL` is required for the application to connect to your database.
- `JWT_SECRET` should be a strong, random string in production.
- `COHERE_API_KEY` can be omitted if you just want to run the API without real AI calls, but ingredient analysis will be limited.

---

### 5.4. Initialize the database

When you run `docker compose up --build -d`, the `postgres` service and the API will start. On first startup, FastAPI’s `lifespan` hook calls `init_db()` and creates the tables using the `DATABASE_URL` value from `.env`.

After the app is up, you can optionally use the admin endpoint to drop all tables:

- `DELETE /admin/drop-db` – drops all tables using `drop_db()` (use with caution).

---

### 5.5. Access the API server

Once `docker compose up --build -d` completes successfully, the API will be available at:

- **Base URL**: `http://localhost:8000/`
- **Interactive docs (Swagger UI)**: `http://localhost:8000/docs`
- **Health check**: `GET /health`

Most routes require a valid JWT in the `Authorization: Bearer <token>` header, as configured in `auth/backend.py`.

---

### 5.6. Celery worker

The Celery worker service (`celery-worker`) is started automatically by Docker Compose using the same image and `.env` file. You do **not** need to run Celery manually.

You can inspect its status and logs with:

```bash
docker compose ps
docker compose logs -f celery-worker
```

---

### 5.7. Running tests

To run the test suite inside the `fast-api` container:

```bash
docker compose exec fast-api pytest
```

The tests use temporary databases and in-memory configurations, and they may set environment variables like `TEST_DATABASE_URL`, `JWT_SECRET`, and `COHERE_API_KEY` internally.

---

## 6. Manual Docker build (alternative)

A multi-stage Dockerfile is provided under `compose/Dockerfile`. It:

- Installs system dependencies (Tesseract, OpenCV libs, PostgreSQL libs).
- Installs Python dependencies.
- Copies the application code into the image.
- Starts the API via Uvicorn.

Example build & run (from project root):

```bash
docker build -f compose/Dockerfile -t nutrilens-api .
docker run -p 8000:8000 --env-file .env nutrilens-api
```

You will still need a running PostgreSQL and Redis instance reachable from the container, and a `.env` file with the variables described above.
