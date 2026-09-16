FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md ./
COPY python ./python
RUN pip install --no-cache-dir .

COPY apps/api ./apps/api
COPY docs/vastu/spec-v1.0/production ./docs/vastu/spec-v1.0/production

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
