"""Seed tests — the DB registry mirrors the code registry and stays idempotent."""
import pytest
from sqlalchemy import func, select

from app import models
from app.database import Base, SessionLocal, engine
from app.seed import seed_registry
from lucas import registry


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def test_seed_writes_all_models(db):
    n = seed_registry(db)
    assert n == len(registry._ROWS)
    count = db.scalar(select(func.count()).select_from(models.ModelRegistryRow))
    assert count == len(registry._ROWS)


def test_seed_is_idempotent(db):
    seed_registry(db)
    seed_registry(db)  # re-run must not duplicate rows
    count = db.scalar(select(func.count()).select_from(models.ModelRegistryRow))
    assert count == len(registry._ROWS)


def test_gated_models_persist_with_reason(db):
    seed_registry(db)
    flux = db.scalar(select(models.ModelRegistryRow).where(
        models.ModelRegistryRow.model_id == "flux-3"))
    assert flux.sellable is False
    assert flux.gate_reason  # non-empty reason stored


def test_current_default_is_sellable(db):
    seed_registry(db)
    h3 = db.scalar(select(models.ModelRegistryRow).where(
        models.ModelRegistryRow.model_id == "minimax-h3-max",
        models.ModelRegistryRow.is_current.is_(True)))
    assert h3.sellable is True
    assert h3.provider_cost_usd == 0.04
