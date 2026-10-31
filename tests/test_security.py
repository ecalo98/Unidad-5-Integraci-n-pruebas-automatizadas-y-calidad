from datetime import UTC, datetime, timedelta

import pytest

from src.security import can_cancel


def test_owner_within_24h():
    now = datetime.now(UTC)
    assert can_cancel("NEW", 1, 1, False, now - timedelta(hours=1), now)

def test_stranger_denied():
    now = datetime.now(UTC)
    assert not can_cancel("NEW", 1, 2, False, now, now)

def test_shipped_denied_even_admin():
    now = datetime.now(UTC)
    assert not can_cancel("SHIPPED", 1, 1, True, now, now)

def test_expired_denied():
    now = datetime.now(UTC)
    assert not can_cancel("NEW", 1, 1, False, now - timedelta(hours=25), now)


FIXED_NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)  # fecha fija: resultado siempre igual


def test_admin_cancels_new_order_of_another_user():
    created = FIXED_NOW - timedelta(hours=48)  # el admin no está sujeto al límite de 24 h
    assert can_cancel("NEW", 1, 99, True, created, FIXED_NOW)


def test_owner_denied_at_exactly_24_hours():
    created = FIXED_NOW - timedelta(hours=24)  # exactamente 24 h: la regla usa "< 24 h"
    assert not can_cancel("NEW", 1, 1, False, created, FIXED_NOW)


# Matriz de autorización: (rol, relación con el pedido, estado, antigüedad, permitido)
AUTH_MATRIX = [
    ("propietario", "NEW", timedelta(hours=1), True),
    ("propietario", "NEW", timedelta(hours=23, minutes=59), True),
    ("propietario", "NEW", timedelta(hours=24), False),
    ("propietario", "NEW", timedelta(hours=25), False),
    ("tercero", "NEW", timedelta(hours=1), False),
    ("administrador", "NEW", timedelta(hours=1), True),
    ("administrador", "NEW", timedelta(hours=48), True),
    ("propietario", "SHIPPED", timedelta(hours=1), False),
    ("administrador", "SHIPPED", timedelta(hours=1), False),
    ("propietario", "CONFIRMED", timedelta(hours=1), True),
]


@pytest.mark.parametrize(
    "role,status,age,allowed",
    AUTH_MATRIX,
    ids=[f"{r}-{s}-{int(a.total_seconds() // 60)}min" for r, s, a, _ in AUTH_MATRIX],
)
def test_authorization_matrix(role, status, age, allowed):
    owner_id = 1
    user_id = 1 if role == "propietario" else 2
    is_admin = role == "administrador"
    assert can_cancel(status, owner_id, user_id, is_admin, FIXED_NOW - age, FIXED_NOW) is allowed
