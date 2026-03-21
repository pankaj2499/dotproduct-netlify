#!/usr/bin/env bash
set -euo pipefail

exec celery -A app.celery_app worker --loglevel="${CELERY_LOGLEVEL:-info}"
