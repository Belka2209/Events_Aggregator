# Events Aggregator API

Сервис-агрегатор мероприятий, который синхронизирует данные из внешнего API провайдера событий и предоставляет интерфейс для управления билетами.

## Основные возможности

- **Автоматическая синхронизация**: Фоновый процесс для периодического получения обновлений о мероприятиях.
- **Управление билетами**: Регистрация пользователей на мероприятия и отмена регистрации.
- **Просмотр мест**: Получение списка доступных мест для конкретного события.
- **Пагинация и фильтрация**: Удобный просмотр списка мероприятий с поддержкой фильтров.
- **Здоровье сервиса**: Эндпоинт `/api/health` для мониторинга состояния приложения и базы данных.

## Технологический стек

- **Язык**: Python 3.11+
- **Фреймворк**: [FastAPI](https://fastapi.tiangolo.com/)
- **База данных**: PostgreSQL
- **ORM**: SQLAlchemy 2.0 (асинхронный режим)
- **Миграции**: Alembic
- **Валидация данных**: Pydantic v2
- **HTTP Клиент**: HTTPX (асинхронный)
- **Менеджер пакетов**: [uv](https://github.com/astral-sh/uv)
- **Контейнеризация**: Docker

## Структура проекта

```text
src/
├── api/          # Маршруты FastAPI и запуск приложения
├── core/         # Настройки, база данных и зависимости
├── models/       # Модели SQLAlchemy
├── repositories/ # Слой доступа к данным (Repository pattern)
├── schemas/      # Схемы Pydantic для API
├── services/     # Бизнес-логика и внешние клиенты
└── usecases/     # Сценарии использования (Clean Architecture)
tests/            # Тесты (pytest)
```

## Быстрый старт

### Предварительные требования

- Установленный `uv` (рекомендуется) или `pip`.
- PostgreSQL (или Docker для запуска в контейнере).

### Установка

1. Клонируйте репозиторий:
   ```bash
   git clone <repository-url>
   cd events-provider-api
   ```

2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   uv sync
   ```

3. Настройте переменные окружения:
   Создайте файл `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```

### Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|-----------------------|
| `POSTGRES_CONNECTION_STRING` | Строка подключения к БД | `postgresql+asyncpg://postgres:postgres@localhost:5432/events_aggregator` |
| `EVENTS_PROVIDER_BASE_URL` | URL внешнего API провайдера | (см. settings.py) |
| `EVENTS_PROVIDER_API_KEY` | API ключ провайдера | `""` |
| `SYNC_INTERVAL_HOURS` | Интервал синхронизации (часы) | `24` |

### Запуск приложения

С помощью `uv`:
```bash
uv run uvicorn src.api.app:app --reload
```

Или через скрипт `run.sh`:
```bash
chmod +x run.sh
./run.sh
```

### Запуск тестов

```bash
uv run pytest
```

## API Документация

После запуска приложения документация доступна по адресам:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Основные эндпоинты

- `GET /api/events/` — Список мероприятий.
- `GET /api/events/{id}/seats/` — Свободные места.
- `POST /api/tickets/register` — Регистрация на событие.
- `DELETE /api/tickets/{event_id}/unregister` — Отмена регистрации.
- `POST /api/sync/` — Принудительный запуск синхронизации.

## Использование Docker

Сборка и запуск контейнера:
```bash
docker build -t events-aggregator .
docker run -p 8000:8000 --env-file .env events-aggregator
```
