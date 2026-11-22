FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY db ./db

RUN useradd --system --uid 10001 servichile
USER servichile

# Cloud Run define PORT (8080 por defecto)
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app.principal:app --host 0.0.0.0 --port ${PORT:-8080}"]
