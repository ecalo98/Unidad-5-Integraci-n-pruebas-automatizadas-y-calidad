"""Casos CP01-CP12 de la matriz, leídos de data/*.csv con csv.DictReader (pruebas parametrizadas)."""
import csv
from pathlib import Path

import pytest

from src.domain import CustomerHasDebt, Order

DATA = Path(__file__).resolve().parent.parent / "data"

# CP08 cambió después del ciclo TDD (Paso 3): el CSV original describe el comportamiento
# anterior (confirmaba dos veces) y la regla nueva exige rechazarlo.
EXPECTED_AFTER_TDD = {"CP08": "ValueError"}

EXCEPTIONS = {"CustomerHasDebt": CustomerHasDebt, "ValueError": ValueError}


def read_csv(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


ORDERS = {row["pedido_id"]: row for row in read_csv("pedidos_prueba.csv")}
CASES = [case for case in read_csv("casos_de_prueba.csv") if case["pedido_id"]]


def build_order(row):
    return Order(total=float(row["total"]), vip=row["es_vip"] == "1", status=row["estado_inicial"])


@pytest.mark.parametrize("case", CASES, ids=[case["caso_id"] for case in CASES])
def test_case_from_csv(case):
    row = ORDERS[case["pedido_id"]]
    expected = EXPECTED_AFTER_TDD.get(case["caso_id"], case["resultado_esperado"])
    order = build_order(row)
    debt = float(row["deuda_cliente"])
    if expected.startswith("CONFIRMED"):
        charge = order.confirm(customer_debt=debt)
        assert order.status == "CONFIRMED"
        assert charge == pytest.approx(float(expected.split("cobro")[1]))
    else:
        with pytest.raises(EXCEPTIONS[expected]):
            order.confirm(customer_debt=debt)
