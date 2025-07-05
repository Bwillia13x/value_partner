# Beta Testing Guide for Value Partner Platform

Welcome to the private beta of **Value Partner**! This guide will help you get the platform running locally, understand the key workflows to test, and know how to report any issues you encounter.

---

## 1. Prerequisites

1. **Python 3.12+** (or Docker Desktop if you prefer containers)
2. **Redis** and **PostgreSQL** services running locally (alternatively use `docker-compose` in the repo)
3. Clone this repository and check out the `main` branch

```bash
$ git clone https://github.com/Bwillia13x/value_partner.git
$ cd value_partner
```

---

## 2. Quick-Start (Local Python Environment)

```bash
# 1. Create & activate a virtual environment
$ python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
$ pip install -r requirements.txt

# 3. Start the FastAPI service (port 8000)
$ uvicorn services.main:app --reload

# 4. In another terminal, start the Celery worker
$ celery -A services.celeryapp worker -l info
```

### Using Docker

```bash
$ docker-compose up --build  # spins up API + Celery + Redis + Postgres
```

The interactive API documentation is now available at **http://localhost:8000/docs**.

---

## 3. Core Workflows to Exercise

| Workflow | Endpoint / Command | Expected Outcome |
|----------|-------------------|------------------|
| Health Check | `GET /health` | Returns `{ "status": "ok" }` |
| Account Reconciliation | `POST /reconcile` | Task queued & processed, response includes `task_id` |
| Market Data Sync | `POST /sync-market-data` | Initiates sync job |
| Portfolio Analytics | `POST /run-analytics` | Returns analytics summary JSON |

> All endpoints return standard HTTP status codes plus a JSON body. Celery task IDs can be queried via the `/tasks/{id}` endpoint.

---

## 4. Smoke Test Script

Run a quick automated test (requires the service running):

```bash
$ python scripts/smoke_test.py
```

The script hits `/health`, triggers a sample Celery job, and checks logs for a successful completion.

---

## 5. Known Limitations (Beta)

1. Authentication & rate limiting are **minimal** – use a dev environment only.
2. Factor library is incomplete; some analytics may be placeholders.
3. CI/CD pipeline not yet wired to production infrastructure.
4. Error handling is basic; please report stack traces.

---

## 6. Reporting Issues / Feedback

1. Open an issue in the GitHub repo using the **Beta Feedback** template.
2. Include steps to reproduce, logs, and screenshots if helpful.
3. For urgent help ping `@maintainers` on Slack (link in repo README).

Thank you for helping us make Value Partner better!
