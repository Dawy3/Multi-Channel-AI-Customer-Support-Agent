#!/bin/bash
set -e

echo "Running database migrations..."

cd /app/models/db_schemes/rag/
alembic upgrade head
cd /app

exec "$@"
