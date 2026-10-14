import pytest

from app.domain import normalize_phone, sync


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+7 999 123-45-67", "+79991234567"),
        ("8 (999) 123 45 67", "+79991234567"),
        ("79991234567", "+79991234567"),
        ("9005551212", "+79005551212"),
        ("123", None),
        ("", None),
        ("не указан", None),
        ("+7 999", None),
        ("+1 999 123 45 67", None),
        (None, None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def _o(id, phone, amount, created, name="n"):
    return {"id": id, "name": name, "phone": phone, "email": "", "amount": amount, "created_at": created}


def test_max_amount_wins():
    r = sync([_o(1, "89991234567", 100, "2026-10-09T00:00:00Z", "a"), _o(2, "+79991234567", 500, "2026-10-01T00:00:00Z", "b")])
    assert [c.name for c in r.clients] == ["b"]


def test_equal_amount_later_wins_regardless_of_input_order():
    old, new = _o(1, "89991234567", 100, "2026-10-01T00:00:00Z", "old"), _o(2, "89991234567", 100, "2026-10-05T00:00:00Z", "new")
    assert sync([old, new]).clients[0].name == "new"
    assert sync([new, old]).clients[0].name == "new"


def test_stats_and_idempotency():
    orders = [_o(1, "89991234567", 1, "2026-10-01T00:00:00Z"), _o(2, "89991234567", 2, "2026-10-01T00:00:00Z"), _o(3, "bad", 9, "2026-10-01T00:00:00Z")]
    first = sync(orders)
    assert first.stats.model_dump() == {"received": 3, "unique": 1, "duplicates_merged": 1, "invalid_dropped": 1}
    assert sync(orders) == first


def test_garbage_input_does_not_crash():
    r = sync([_o(1, "89991234567", "abc", "oops"), "строка", _o(2, "89991234567", None, "2026-10-01T00:00:00Z")])
    assert r.stats.received == 3
    assert r.stats.invalid_dropped == 1
    assert len(r.clients) == 1
