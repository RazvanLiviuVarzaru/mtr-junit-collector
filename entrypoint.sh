#!/bin/sh
set -e

# Default values if env vars are not set
: "${GUNICORN_WORKERS:=1}"
: "${GUNICORN_HOST:=127.0.0.1}"
: "${GUNICORN_PORT:=8080}"
: "${GUNICORN_LOGLEVEL:=INFO}"

exec gunicorn app.main:app \
  --workers "$GUNICORN_WORKERS" \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "$GUNICORN_HOST:$GUNICORN_PORT" \
  --access-logfile - \
  --error-logfile - \
  --log-level $GUNICORN_LOGLEVEL