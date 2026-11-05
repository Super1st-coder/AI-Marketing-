# LucaCredit — Central Billing Service

The platform pricing/billing source of truth (Marco, 2026-09-09). Every module estimates and
charges Lucas through this service instead of keeping its own price table. V1 = spend protection:
the ledger + the $100/org video cap (Gate 1).

**Model:** org = wallet · brand = license · Lucas = fuel. `100 Lucas = $1`.
`lucas = ceil(provider_cost_usd × multiplier × qty ÷ 0.01)` (computed with `Decimal`, exact).

## Layout

```
lucas/            pure domain core (no DB/framework) — the reference-prototype parity
  engine.py         lots, estimate→reserve→commit→release, FIFO, +10% tolerance, auto-release
  registry.py       versioned price table; unconfirmed models GATED (refuse to price)
  service.py        in-memory 4-call facade + Gate-1 video cap (the behavioral spec)
app/              the deployable service
  models.py         SQLAlchemy ORM (organizations, lots, reservations, reservation_steps,
                    ledger_entries, model_registry) — idempotency enforced in the schema
  repository.py     the 4 calls against Postgres, reusing the domain rules for the math
  main.py           FastAPI app (X-Internal-Key auth) — routes wrap the repository 1:1
  seed.py           seed/sync the DB model_registry from the code registry
alembic/          migrations (initial ledger schema)
  pricing.py        DB-driven pricing: price at current version, freeze on reserve, edit live
  reconcile.py      weekly price-drift job (observed cost/unit vs registry, >10% alerts)
tests/            88 tests: domain (40) + repository (16) + API (15) + seed (4) + pricing (8) + reconcile (6)
```

## The contract (what Durval's video module calls)

All under `/api/v1/billing`, header `X-Internal-Key: <LUCA_CREDITS_INTERNAL_KEY>`. Callers pass
`model_id` + `qty` (video seconds / images / 1k tokens / 1k chars), never Lucas.

| call | idempotent by | notes |
|------|---------------|-------|
| `POST /estimate` | — | FREE, holds nothing, never blocks. Refuses gated models |
| `POST /reserve`  | `job_id` | blocks on balance + Gate-1 video cap; freezes `model_version` |
| `POST /commit`   | `job_id:step_id` | real usage; FIFO lot consumption; +10% tolerance flag |
| `POST /release`  | `job_id` (terminal) | SETTLED if any commits else RELEASED; frees the unspent |
| `GET  /balance/{org_id}` | — | for the header credit counter |

Registry (platform pricing authority), under `/api/v1`:

| call | notes |
|------|-------|
| `GET  /registry` | current prices + gated models, read from the DB (Durval / drift job) |
| `POST /registry/price` | edit a price WITHOUT a deploy — new version + notify finance |
| `POST /registry/reconcile` | drift check: observed cost/unit (LangFuse) vs registry → >threshold alerts |

## Run

```bash
python -m venv .venv && ./.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env          # fill DATABASE_* + LUCA_CREDITS_INTERNAL_KEY
./.venv/Scripts/alembic upgrade head
./.venv/Scripts/python -m app.seed
./.venv/Scripts/uvicorn app.main:app --reload
./.venv/Scripts/python -m pytest -q   # 71 passing (SQLite, no Postgres needed)
```

## Registry is the runtime source of truth

Pricing reads the DB `model_registry` table (seeded from `lucas/registry.py`, which remains the
parity/reference). A price EDIT (`POST /registry/price`) inserts a new version, flips `is_current`,
and notifies finance — **no deploy**. In-flight jobs keep the version frozen at reserve, so a
mid-job edit never re-prices them. `POST /registry/reconcile` compares observed cost/unit to the
registry and alerts on >10% drift.

## V1 boundaries (deliberately deferred)

- **Drift feed:** the reconciliation *logic* is built and tested; the LangFuse trace feed that
  supplies observed cost/unit in production is Luis's integration (HLC-9).
- **Gated models** (`flux-3`, `seedance-2.5-*`, full `veo-3.1`, `kling`) refuse to price until a
  confirmed cost is set via `POST /registry/price` (needs Luis's real BytePlus/FLUX rates, HLC-9).
- **Finance notify** is a logged event seam (`pricing.set_notifier`); wire it to email later.
- **Pay/purchase flow + monthly license renewal** — pending scope confirmation (15-day V1 vs phased).
