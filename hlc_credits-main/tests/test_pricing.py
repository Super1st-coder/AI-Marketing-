"""DB-driven pricing tests — edit-without-deploy, version freezing, gating from the DB."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app import models, pricing
from app.database import Base, SessionLocal, engine
from app.repository import CreditsRepository
from app.seed import seed_registry
from lucas.registry import UnpricedModel

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
CYCLE_END = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    seed_registry(s)
    try:
        yield s
    finally:
        s.close()


# ── pricing reads the DB ────────────────────────────────────────────────────────
def test_price_current_from_db(db):
    lucas, version = pricing.price_current(db, "minimax-h3-max", 8)
    assert lucas == 160
    assert version == "1"


def test_gated_model_refuses_from_db(db):
    with pytest.raises(UnpricedModel):
        pricing.price_current(db, "flux-3", 8)


def test_unknown_model_raises(db):
    with pytest.raises(pricing.UnknownModel):
        pricing.price_current(db, "no-such-model", 1)


# ── edit price WITHOUT a deploy ─────────────────────────────────────────────────
def test_set_price_supersedes_version_and_prices_new(db):
    pricing.set_price(db, "minimax-h3-max", provider_cost_usd=0.08, edited_by="marco")
    lucas, version = pricing.price_current(db, "minimax-h3-max", 8)
    assert version == "2"        # new current version
    assert lucas == 320          # $0.08 × 8 × 5 ÷ 0.01 = 320 (doubled)
    # old row kept, no longer current
    rows = db.scalars(select(models.ModelRegistryRow).where(
        models.ModelRegistryRow.model_id == "minimax-h3-max")).all()
    assert len(rows) == 2
    assert sum(1 for r in rows if r.is_current) == 1


def test_set_price_notifies_finance(db):
    events = []
    pricing.set_notifier(events.append)
    try:
        pricing.set_price(db, "minimax-h3-max", provider_cost_usd=0.05, edited_by="marco")
    finally:
        pricing.set_notifier(lambda e: None)
    assert events and events[0]["event"] == "registry_price_edit"
    assert events[0]["to_version"] == "2"
    assert events[0]["new_cost_usd"] == 0.05


def test_ungating_requires_confirmed_price(db):
    # flipping a gated model sellable without a real cost must fail
    with pytest.raises(ValueError):
        pricing.set_price(db, "flux-3", sellable=True)
    # with a confirmed cost it succeeds and prices
    pricing.set_price(db, "flux-3", sellable=True, provider_cost_usd=0.10, verified_at="2026-09-30")
    lucas, _ = pricing.price_current(db, "flux-3", 8)
    assert lucas == 400  # $0.10 × 8 × 5 ÷ 0.01


# ── version freezing: a price edit mid-job doesn't re-price the reservation ──────
def test_commit_uses_frozen_version_not_new_price(db):
    repo = CreditsRepository(db)
    repo.grant_license("org1", 1_000_000, CYCLE_END)
    repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 8, now=NOW)  # v1: 160
    # price DOUBLES after the reserve
    pricing.set_price(db, "minimax-h3-max", provider_cost_usd=0.08, edited_by="marco")
    # commit still charges at the frozen v1 price, not the new v2
    charged = repo.commit("org1", "job1", "s1", "minimax-h3-max", 8, now=NOW)
    assert charged == 160  # frozen, NOT 320
    res = db.get(models.Reservation, "job1")
    assert res.model_version == "1"


def test_new_reservation_after_edit_uses_new_price(db):
    repo = CreditsRepository(db)
    repo.grant_license("org1", 1_000_000, CYCLE_END)
    pricing.set_price(db, "minimax-h3-max", provider_cost_usd=0.08, edited_by="marco")
    res = repo.reserve("org1", "job2", "video_segment", "b", "minimax-h3-max", 8, now=NOW)
    assert res.lucas_reserved == 320  # new job gets the new price
    assert res.model_version == "2"
