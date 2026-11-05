"""V1 alignment tests (Marco's confirmed answers):
- license grant = price × 50, fixed, independent of the registry multiplier;
- the $100 cap counts ONLY video_segment (generation), not the cheaper video steps;
- usage alerts fire once each at 50/75/90%.
"""
from datetime import datetime, timezone

import pytest

from app import usage_alerts
from app.database import Base, SessionLocal, engine
from app.repository import CreditsRepository, VideoCapExceeded
from app.seed import seed_registry
from lucas.engine import Account, lucas_for_license

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
CYCLE_END = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def repo():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    seed_registry(db)
    try:
        yield CreditsRepository(db)
    finally:
        db.close()


# ── license grant = price × 50 (fixed) ────────────────────────────────────────
def test_lucas_for_license_curve():
    assert lucas_for_license(750) == 37_500
    assert lucas_for_license(1000) == 50_000
    assert lucas_for_license(650) == 32_500
    assert lucas_for_license(550) == 27_500


def test_grant_is_not_the_10pct_literal():
    # 10% of $750 at 100 Lucas/$1 would be 7,500 — 5x too few. The ×50 rule gives 37,500.
    assert lucas_for_license(750) != 7_500


def test_account_grant_license_for_price():
    acct = Account("org1")
    acct.grant_license_for_price("lic", 750, CYCLE_END)
    assert acct.license_balance(NOW) == 37_500


def test_repo_grant_license_for_price(repo):
    repo.grant_license_for_price("org1", 700, CYCLE_END)
    assert repo.available("org1", NOW) == 35_000


# ── $100 cap counts ONLY video_segment ────────────────────────────────────────
def test_non_generation_video_actions_do_not_hit_the_cap(repo):
    repo.grant_license("org1", 1_000_000, CYCLE_END)
    # 40 storyboard reserves × 300 = 12,000 > the 10,000 cap — but storyboard isn't
    # video_segment, so the cap must NOT apply.
    for i in range(40):
        repo.reserve("org1", f"sb{i}", "video_storyboard", "b", "minimax-h3-max", 15, now=NOW)
    assert repo.video_spend("org1") == 0        # none of it counts as generation spend
    # video_segment IS capped: 33×300=9,900 ok, the 34th trips it.
    for i in range(33):
        repo.reserve("org1", f"seg{i}", "video_segment", "b", "minimax-h3-max", 15, now=NOW)
    with pytest.raises(VideoCapExceeded):
        repo.reserve("org1", "seg33", "video_segment", "b", "minimax-h3-max", 15, now=NOW)


# ── usage alerts at 50/75/90% ─────────────────────────────────────────────────
def test_usage_alerts_fire_once_per_threshold(repo):
    events = []
    usage_alerts.set_alert_notifier(events.append)
    try:
        repo.grant_license("org1", 1_000, CYCLE_END)  # 1,000 Lucas granted
        repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 50, now=NOW)  # reserve 1000

        repo.commit("org1", "job1", "s1", "minimax-h3-max", 30, now=NOW)  # 600 consumed → 60%
        assert {e["threshold"] for e in events} == {0.50}

        repo.commit("org1", "job1", "s2", "minimax-h3-max", 15, now=NOW)  # +300 → 900 → 90%
        assert {e["threshold"] for e in events} == {0.50, 0.75, 0.90}

        before = len(events)
        repo.commit("org1", "job1", "s3", "minimax-h3-max", 1, now=NOW)   # +20 → no new threshold
        assert len(events) == before                                       # nothing refires
    finally:
        usage_alerts.set_alert_notifier(lambda e: None)


def test_usage_alert_payload_has_topup_and_pct(repo):
    events = []
    usage_alerts.set_alert_notifier(events.append)
    try:
        repo.grant_license("org1", 1_000, CYCLE_END)
        repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 50, now=NOW)
        repo.commit("org1", "job1", "s1", "minimax-h3-max", 30, now=NOW)  # 60%
        e = events[0]
        assert e["event"] == "usage_alert"
        assert e["org_id"] == "org1"
        assert 0 < e["pct_used"] <= 1
        assert "top_up_url" in e   # None in tests (unset), but the key is always present
    finally:
        usage_alerts.set_alert_notifier(lambda e: None)
