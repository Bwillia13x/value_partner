### ---------- Builder Stage ----------
FROM python:3.11-slim AS builder

WORKDIR /install

COPY services/requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y build-essential && \
    pip install --upgrade pip wheel && \
    pip wheel --no-cache-dir -r requirements.txt

### ---------- Runtime Stage ----------
FROM python:3.11-slim

WORKDIR /app

# Copy wheels from builder stage and install
COPY --from=builder /install /wheels
RUN pip install --no-cache /wheels/*.whl && rm -rf /wheels

# Copy application code
COPY services/app ./app

# Security best-practice: run as non-root
RUN useradd -m uvicorn
USER uvicorn

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]