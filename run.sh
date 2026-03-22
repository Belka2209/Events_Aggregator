#!/usr/bin/env bash
# Скрипт для запуска приложения

# Применение миграций (если используются)
# uv run alembic upgrade head

# Запуск сервера
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
