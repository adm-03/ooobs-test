"""Чистая логика синхронизации: нормализация телефонов и дедупликация. Без I/O."""

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


class Client(BaseModel):
    name: str
    phone: str
    email: str
    amount: float | int


class Stats(BaseModel):
    received: int
    unique: int
    duplicates_merged: int
    invalid_dropped: int


class SyncResult(BaseModel):
    clients: list[Client]
    stats: Stats


def normalize_phone(raw: object) -> str | None:
    """Приводит номер к +7XXXXXXXXXX или возвращает None, если это невозможно."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 11 and digits[0] in "78":
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"+7{digits}"


def _parse_dt(value: object) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _rank(order: dict[str, Any]) -> tuple[float, datetime]:
    # Больший amount важнее; при равенстве побеждает более поздняя заявка.
    return float(order.get("amount") or 0), _parse_dt(order.get("created_at"))


def sync(orders: list[dict[str, Any]]) -> SyncResult:
    """Результат целиком зависит от входа — повторный запуск даёт тот же ответ (идемпотентно)."""
    best: dict[str, dict[str, Any]] = {}  # dict хранит порядок первого появления телефона
    invalid = 0
    for order in orders:
        phone = normalize_phone(order.get("phone"))
        if phone is None:
            invalid += 1
            continue
        current = best.get(phone)
        if current is None or _rank(order) > _rank(current):
            best[phone] = order

    clients = [
        Client(
            name=o.get("name") or "",
            phone=phone,
            email=o.get("email") or "",
            amount=o.get("amount") or 0,
        )
        for phone, o in best.items()
    ]
    valid = len(orders) - invalid
    return SyncResult(
        clients=clients,
        stats=Stats(
            received=len(orders),
            unique=len(clients),
            duplicates_merged=valid - len(clients),
            invalid_dropped=invalid,
        ),
    )
