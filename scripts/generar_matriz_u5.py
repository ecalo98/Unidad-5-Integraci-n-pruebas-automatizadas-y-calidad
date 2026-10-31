"""Genera docs/matriz_resultados_u5.csv: resultado esperado vs resultado real de CP01-CP15.

Ejecuta las reglas reales del proyecto (src/) con los datos de data/*.csv. No modifica el código ni los datos.
Uso (desde la raíz del proyecto):  python scripts/generar_matriz_u5.py
"""
import csv
import sys
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.application import OrderService
from src.domain import CustomerHasDebt, Order
from src.repository import OrderRow, SqlOrderRepository, make_engine

# Clasificación de cada caso y regla que verifica (la matriz exige >= 5 éxito, 4 error y 3 límite)
META = {
    "CP01": ("Éxito", "Pedido regular sin descuento", "test_matriz_csv.py::test_case_from_csv[CP01]"),
    "CP02": ("Éxito", "Descuento VIP 15%", "test_matriz_csv.py::test_case_from_csv[CP02]"),
    "CP03": ("Error", "Cliente con deuda no confirma", "test_matriz_csv.py::test_case_from_csv[CP03]"),
    "CP04": ("Error", "Total cero no confirma", "test_matriz_csv.py::test_case_from_csv[CP04]"),
    "CP05": ("Error", "Total negativo no confirma", "test_matriz_csv.py::test_case_from_csv[CP05]"),
    "CP06": ("Éxito", "Descuento VIP 15% en total alto", "test_matriz_csv.py::test_case_from_csv[CP06]"),
    "CP07": ("Límite", "Total mínimo positivo (0.01) con VIP", "test_matriz_csv.py::test_case_from_csv[CP07]"),
    "CP08": ("Error", "No confirmar dos veces (regla nueva por TDD)", "test_order.py::test_cannot_confirm_twice"),
    "CP09": ("Éxito", "Descuento VIP 15%", "test_matriz_csv.py::test_case_from_csv[CP09]"),
    "CP10": ("Éxito", "Pedido regular sin descuento", "test_matriz_csv.py::test_case_from_csv[CP10]"),
    "CP11": ("Error", "Deuda bloquea aun siendo VIP", "test_matriz_csv.py::test_case_from_csv[CP11]"),
    "CP12": ("Límite", "Redondeo del descuento a 2 decimales", "test_matriz_csv.py::test_case_from_csv[CP12]"),
    "CP13": ("Error", "Pasarela rechaza el pago", "test_service.py::test_gateway_rejected_vip_200"),
    "CP14": ("Éxito", "Commit hace visible el registro", "test_repository.py::test_repository_commit_order_250"),
    "CP15": ("Límite", "Rollback deja la base sin cambios", "test_repository.py::test_repository_rollback"),
}
EXPECTED_AFTER_TDD = {"CP08": "ValueError (already confirmed)"}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def real_order_case(row):
    order = Order(total=float(row["total"]), vip=row["es_vip"] == "1", status=row["estado_inicial"])
    try:
        charge = order.confirm(customer_debt=float(row["deuda_cliente"]))
    except (CustomerHasDebt, ValueError) as exc:
        return f"{type(exc).__name__}" + (" (already confirmed)" if "already" in str(exc) else "")
    return f"CONFIRMED, cobro {charge:.2f}"


def real_gateway_rejected():
    gateway = Mock()
    gateway.charge.return_value = False
    try:
        OrderService(gateway).checkout(Order(200, vip=True))
    except RuntimeError as exc:
        return f"RuntimeError: {exc}; cobro intentado {gateway.charge.call_args.args[0]:.2f}"
    return "sin error"


def real_commit():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(2, Order(250))
        session.commit()
    with Session(engine) as other:
        row = other.scalar(select(OrderRow).where(OrderRow.id == 2))
    return "Registro visible después de commit" if row else "Registro ausente"


def real_rollback():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        session.rollback()
        row = session.scalar(select(OrderRow).where(OrderRow.id == 1))
    return "Registro ausente después de rollback" if row is None else "Registro presente"


def main():
    pedidos = {r["pedido_id"]: r for r in read_csv(ROOT / "data" / "pedidos_prueba.csv")}
    casos = read_csv(ROOT / "data" / "casos_de_prueba.csv")
    out = []
    for caso in casos:
        cid = caso["caso_id"]
        tipo, regla, prueba = META[cid]
        esperado = EXPECTED_AFTER_TDD.get(cid, caso["resultado_esperado"])
        if caso["pedido_id"]:
            row = pedidos[caso["pedido_id"]]
            entrada = (f"pedido {row['pedido_id']}: total={row['total']}, vip={row['es_vip']}, "
                       f"deuda={row['deuda_cliente']}, estado inicial={row['estado_inicial']}")
            real = real_order_case(row)
        elif cid == "CP13":
            entrada, real = "VIP total=200; mock de pasarela devuelve False", real_gateway_rejected()
        elif cid == "CP14":
            entrada, real = "guardar pedido id=2 total=250 y session.commit()", real_commit()
        else:
            entrada, real = "guardar pedido id=1 total=120 y session.rollback()", real_rollback()
        ok = real.startswith(esperado)  # el real puede añadir detalle (p. ej. el cobro intentado)
        out.append({
            "caso_id": cid, "tipo": tipo, "regla": regla, "entrada": entrada,
            "resultado_esperado": esperado, "resultado_real": real,
            "estado": "PASSED" if ok else "FAILED", "prueba": prueba,
            "nota": ("Antes del TDD el CSV esperaba CONFIRMED (el código permitía confirmar dos veces)"
                     if cid == "CP08" else caso["nota"]),
        })
    target = ROOT / "docs" / "matriz_resultados_u5.csv"
    target.parent.mkdir(exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    for r in out:
        print(f"{r['caso_id']}  {r['tipo']:<7} {r['estado']}  esperado={r['resultado_esperado']!r}  real={r['resultado_real']!r}")
    print(f"\nGenerado: {target}")


if __name__ == "__main__":
    main()
