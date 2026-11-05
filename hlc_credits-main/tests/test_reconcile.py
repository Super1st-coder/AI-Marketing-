"""Drift reconciliation tests — observed cost/unit vs registry, >10% alerts."""
import pytest

from app.database import Base, SessionLocal, engine
from app.reconcile import reconcile, reconcile_report
from app.seed import seed_registry


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


def test_no_alert_within_threshold(db):
    # h3max registry $0.04; observed $0.042 = 5% off → no alert
    assert reconcile(db, {"minimax-h3-max": 0.042}) == []


def test_alert_when_undercharging(db):
    # observed $0.10 vs registry $0.04 = 150% off → the ADK-style under-cost problem
    alerts = reconcile(db, {"minimax-h3-max": 0.10})
    assert len(alerts) == 1
    a = alerts[0]
    assert a["kind"] == "drift"
    assert a["direction"] == "under-charging"
    assert a["deviation_pct"] == 150.0


def test_alert_when_overcharging(db):
    # observed $0.02 vs registry $0.04 = 50% off, registry too high
    alerts = reconcile(db, {"minimax-h3-max": 0.02})
    assert alerts[0]["direction"] == "over-charging"


def test_unregistered_model_flagged(db):
    alerts = reconcile(db, {"brand-new-model": 0.20})
    assert alerts[0]["kind"] == "unregistered"


def test_gated_but_used_flagged(db):
    # flux-3 is gated (no price) but real usage observed → needs pricing, not a drift %
    alerts = reconcile(db, {"flux-3": 0.10})
    assert alerts[0]["kind"] == "gated_but_used"


def test_report_shape(db):
    rep = reconcile_report(db, {"minimax-h3-max": 0.10, "nano-banana-2": 0.067})
    assert rep["models_checked"] == 2
    assert rep["alert_count"] == 1        # only h3max drifted
    assert rep["threshold_pct"] == 10.0
