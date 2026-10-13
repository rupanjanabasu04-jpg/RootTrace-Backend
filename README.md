# RootTrace backend

Step 1 foundation for the RootTrace API. It includes FastAPI, SQLAlchemy,
PostgreSQL configuration, Alembic, environment settings, local CORS, and a
health endpoint. No product features are implemented yet.

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure the PostgreSQL URL in `.env`. The expected shape is:

   ```text
   DATABASE_URL=postgresql+psycopg://<username>:<password>@localhost:5432/<database>
   ```

   `.env` is intentionally ignored by Git. Alembic reads this same URL, so the
   application and migrations always target the same database.

## Run locally

```bash
uvicorn app.main:app --reload
```

The API starts at `http://127.0.0.1:8000`. The interactive documentation is at
`http://127.0.0.1:8000/docs`.

## Health check

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{"status":"ok"}
```

## Database migrations

Alembic is prepared but there are no models or migrations in Step 1. Once a
future feature introduces a model, create a migration with:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```
