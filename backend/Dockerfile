FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_HEADLESS=true

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY --from=builder /build/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /tmp/requirements.txt && \
    playwright install --with-deps chromium && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /wheels /tmp/requirements.txt /root/.cache


COPY backend /app/backend
COPY Conectividade /app/Conectividade
COPY config.ini /app/config.ini

RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/backend/app/data && \
    chown -R appuser:appuser /app

# USER appuser


EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
