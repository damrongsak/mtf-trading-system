FROM python:3.13-slim
WORKDIR /app
COPY services/api-gateway/app /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic psycopg[binary] sqlalchemy asyncpg
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
