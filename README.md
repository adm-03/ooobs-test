# Orders sync

Забирает заявки с `https://test.ooobs.ru/api/orders`, нормализует телефоны к `+7XXXXXXXXXX`,
дедуплицирует по телефону (max `amount`, при равенстве — позже `created_at`).

- `GET /` и `GET /api/clients` — результат (кэш 30 с, при сбое источника отдаётся последний снимок)
- `POST /api/sync` — принудительная синхронизация; результат заменяется целиком, поэтому повтор идемпотентен
- `GET /health`

Запуск: `uv run uvicorn app.main:app`. Тесты: `uv run pytest`. Деплой: Dockerfile / `render.yaml` (Render, Railway, Fly).

Vercel: репозиторий деплоится без настроек (FastAPI находится по `app/main.py`).
