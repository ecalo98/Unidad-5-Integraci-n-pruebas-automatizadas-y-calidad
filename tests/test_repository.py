import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.domain import Order
from src.repository import OrderRow, SqlOrderRepository, make_engine


def test_repository_commit():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        session.commit()
        assert session.scalar(select(OrderRow).where(OrderRow.id == 1)).total == 120

def test_repository_rollback():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        session.rollback()
        assert session.scalar(select(OrderRow).where(OrderRow.id == 1)) is None


def test_repository_commit_order_250():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(2, Order(250))
        session.commit()
        row = session.scalar(select(OrderRow).where(OrderRow.id == 2))
        assert row.id == 2
        assert row.total == 250
        assert row.status == "NEW"


def test_repository_commit_is_visible_from_a_new_session():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(2, Order(250))
        session.commit()
    with Session(engine) as other_session:  # sesión distinta: solo ve lo confirmado
        row = other_session.scalar(select(OrderRow).where(OrderRow.id == 2))
        assert row is not None
        assert row.total == 250


def test_repository_rollback_is_not_visible_from_a_new_session():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(3, Order(80))
        session.rollback()
    with Session(engine) as other_session:
        assert other_session.scalar(select(OrderRow).where(OrderRow.id == 3)) is None


def test_repository_rejects_duplicate_id():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        session.commit()
        SqlOrderRepository(session).save(1, Order(999))  # mismo id: viola la llave primaria
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert session.scalar(select(OrderRow).where(OrderRow.id == 1)).total == 120
