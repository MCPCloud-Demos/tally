FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
        "fastapi[standard]>=0.115" \
        "sqlmodel>=0.0.22" \
        "pydantic-settings>=2.6" \
        "psycopg[binary]>=3.2"

COPY app ./app

EXPOSE 8080
CMD ["fastapi", "run", "app/main.py", "--port", "8080"]
