# Backend production image: FastAPI served by gunicorn + uvicorn workers.
FROM python:3.12-slim

# Avoid .pyc files and buffered stdout; helps container logging.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY app ./app

# Document the port; the platform may override via $PORT.
EXPOSE 8000

# Start command. Uses $PORT if the platform provides one (Render/Railway),
# else defaults to 8000. Uvicorn workers give async support under gunicorn.
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
