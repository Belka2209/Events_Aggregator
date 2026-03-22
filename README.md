# Events Aggregator

Backend сервис-агрегатор для работы с Events Provider API.

## Описание

Сервис предоставляет REST API для управления событиями и мероприятиями с дополнительной функциональностью:

- Фоновая синхронизация событий раз в день
- Кэширование данных
- Расширенная фильтрация и пагинация
- Валидация данных при регистрации

## Технологический стек

- **Python 3.11+**
- **FastAPI** - веб-фреймворк
- **SQLAlchemy (async)** - ORM
- **PostgreSQL** - база данных
- **httpx** - HTTP клиент для работы с Events Provider API
- **uv** - менеджер пакетов
- **ruff** - линтер и форматтер

## Установка

### Требования

- Python 3.11+
- uv (менеджер пакетов)
- PostgreSQL

### Шаги установки

1. Клонируйте репозиторий:

```bash
git clone <repository-url>
cd Events_Provider_API
```

2. Установите зависимости:

```bash
uv sync
```

3. Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

4. Отредактируйте `.env` и укажите ваши настройки:

```env
# PostgreSQL settings
POSTGRES_CONNECTION_STRING=postgresql+asyncpg://postgres:password@localhost:5432/events_aggregator
POSTGRES_DATABASE_NAME=events_aggregator
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=password

# Events Provider API
EVENTS_PROVIDER_API_KEY=your-api-key-here
```

5. Запустите сервер:

```bash
uv run uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check

```
GET /api/health
```

Проверка доступности сервиса.

### Синхронизация

```
POST /api/sync/trigger
```

Ручной запуск синхронизации событий.

### События

```
GET /api/events?page=1&page_size=20&date_from=YYYY-MM-DD
```

Получение списка событий с пагинацией.

Параметры:
- `page` - номер страницы (по умолчанию 1)
- `page_size` - размер страницы (по умолчанию 20, макс 100)
- `date_from` - фильтр по дате события (формат YYYY-MM-DD)

```
GET /api/events/{event_id}
```

Получение деталей события.

### Места

```
GET /api/events/{event_id}/seats
```

Получение списка свободных мест для события (кэшируется на 30 секунд).

### Билеты

```
POST /api/tickets
```

Регистрация на событие.

Request body:
```json
{
  "event_id": "event-uuid",
  "first_name": "Иван",
  "last_name": "Иванов",
  "email": "ivan@example.com",
  "seat": "A15"
}
```

```
DELETE /api/tickets/{ticket_id}
```

Отмена регистрации.

## Запуск тестов

```bash
uv run pytest
```

## Проверка кода

```bash
# Форматирование
uv run ruff format .

# Линтинг
uv run ruff check --fix .
```

## Структура проекта

```
.
├── src/
│   ├── api/
│   │   ├── app.py              # FastAPI приложение
│   │   └── routes/             # API endpoints
│   ├── core/
│   │   ├── database.py         # Настройки БД
│   │   └── settings.py         # Конфигурация приложения
│   ├── models/                 # SQLAlchemy модели
│   ├── repositories/           # Репозитории для работы с БД
│   ├── schemas/                # Pydantic схемы
│   ├── services/
│   │   ├── background_sync.py  # Фоновая синхронизация
│   │   ├── events_paginator.py # Пагинатор событий
│   │   └── events_provider_client.py  # Клиент Events Provider API
│   └── usecases/
│       └── sync_events.py      # Use case для синхронизации
├── tests/
│   └── test_events_provider_client.py
├── .github/workflows/
│   └── ruff.yml                # CI для проверки кода
├── pyproject.toml
└── README.md
```

## Архитектура

Проект следует паттерну Repository для работы с базой данных и использует dependency injection для внедрения зависимостей.

### Основные компоненты:

1. **EventsProviderClient** - клиент для работы с внешним Events Provider API
2. **Repositories** - абстракция для работы с базой данных
3. **Usecases** - бизнес-логика приложения
4. **API Routes** - HTTP endpoints

## Лицензия

MIT
