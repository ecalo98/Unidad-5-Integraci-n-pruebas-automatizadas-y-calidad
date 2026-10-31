# Unidad 5 CLN: Integración, pruebas y calidad (Actividad 5)

Proyecto base de pedidos con pruebas unitarias, de integración (SQLAlchemy sobre SQLite en memoria), con mocks
(pasarela de pago) y de autorización, más un pipeline de GitHub Actions.
Es un ejemplo didáctico: **no** corresponde a la empresa del PIA (Sazón Urbano), cuyas pruebas se entregan por separado.

**Equipo 3** · Componentes de Lógica de Negocios · FIME UANL

## Instalación y ejecución

Requisitos: Python 3.11 o superior, Git.

```powershell
# Windows PowerShell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

| Qué | Comando |
|---|---|
| Todas las pruebas | `python -m pytest -v` |
| Estilo y calidad (Ruff) | `python -m ruff check src tests` |
| Cobertura con reporte HTML (mínimo 80%) | `python -m pytest -v --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=80` |
| Matriz de resultados reales vs esperados | `python scripts/generar_matriz_u5.py` (escribe `docs/matriz_resultados_u5.csv`) |

El reporte HTML queda en `htmlcov/index.html` (ábrelo en el navegador).

## Arquitectura

```
Usuario/API → Application Service → Entidades / Reglas de dominio
                      ↓ puertos
              Repositorio | Pasarela de pago
                      ↓ adaptadores
                SQLAlchemy | API externa (simulada con Mock)
```

| Archivo | Responsabilidad | Pruebas |
|---|---|---|
| `src/domain.py` | Reglas de pedidos (`Order.confirm`: total positivo, deuda, descuento VIP 15%, no confirmar dos veces) | `tests/test_order.py`, `tests/test_matriz_csv.py` |
| `src/application.py` | `OrderService.checkout`: confirma y cobra mediante la pasarela | `tests/test_service.py` (Mock) |
| `src/repository.py` | Persistencia con SQLAlchemy (`OrderRow`, `SqlOrderRepository`) | `tests/test_repository.py` (commit, rollback, unicidad) |
| `src/security.py` | `can_cancel`: política de cancelación (enviado nunca; admin sí; propietario solo antes de 24 h) | `tests/test_security.py` |

El dominio no importa SQLAlchemy ni bibliotecas de pagos; las pruebas unitarias no usan base de datos y las de
servicio sustituyen la pasarela por un `Mock`, por lo que nunca se realiza un cobro real.

## Datos de prueba (`data/`)

`pedidos_prueba.csv`, `clientes_prueba.csv` y `casos_de_prueba.csv` son datos ficticios. No se cargan solos:
`tests/test_matriz_csv.py` los lee con `csv.DictReader` y ejecuta CP01 a CP12 como pruebas parametrizadas.
CP13 a CP15 (pago rechazado, commit y rollback) se cubren en `test_service.py` y `test_repository.py`.
La base `pedidos_prueba.sqlite3` y `cargar_datos_demo.py` son opcionales y no los usa pytest.

## Cambios respecto al proyecto base

Solo en `src/domain.py` hay un cambio de comportamiento: la regla nueva "no confirmar un pedido ya confirmado"
(Paso 3, TDD). Además, Ruff corrigió automáticamente el orden de imports y el alias `datetime.UTC`
(sin efecto en el comportamiento). El detalle está en el reporte de la actividad.

## Integración continua

`.github/workflows/ci.yml` (sin cambios) ejecuta en cada push o pull request: Ruff, pytest con cobertura mínima de 80%
y compilación de `src/`. La protección obligatoria de merge requiere configurar *branch protection* en GitHub.
