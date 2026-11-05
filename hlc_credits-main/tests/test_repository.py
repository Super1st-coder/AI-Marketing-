"""Repository tests — the DB-backed ledger against SQLite. Same rules as the in-memory
parity suite, now persisted: idempotency, FIFO, +10% tolerance, release, the video cap."""
from datetime import datetime, timedelta, timezone

import pytest

from app.database import Base, SessionLocal, engine
from app.repository import (
    CreditsRepository,
    FreeActionBilled,
    ReservationNotFound,
    VideoCapExceeded,
)
from app.seed import seed_registry
from lucas.engine import InsufficientCredits
from lucas.registry import UnpricedModel

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
CYCLE_END = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def repo():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    seed_registry(db)  # DB registry is the runtime price source now
    try:
        yield CreditsRepository(db)
    finally:
        db.close()


def _funded(repo, lucas=1_000_000, org="org1"):
    repo.grant_license(org, lucas, CYCLE_END)
    return repo


# ── balance math persists ─────────────────────────────────────────────────────
def test_available_license_plus_purchased_minus_reserved(repo):
    repo.grant_license("org1", 10_000, CYCLE_END)
    repo.add_purchased("org1", 10_000, usd_paid=100.0)
    assert repo.available("org1", NOW) == 20_000
    repo.reserve("org1", "job1", "video_segment", "brand1", "minimax-h3-max", 8, now=NOW)
    # h3max 8s = 160 Lucas held
    assert repo.available("org1", NOW) == 20_000 - 160


def test_estimate_is_free_no_rows(repo):
    _funded(repo)
    before = repo.available("org1", NOW)
    assert repo.estimate("minimax-h3-max", 8) == 160
    assert repo.available("org1", NOW) == before


def test_estimate_refuses_gated_model(repo):
    with pytest.raises(UnpricedModel):
        repo.estimate("flux-3", 8)


# ── idempotency (schema-enforced) ──────────────────────────────────────────────
def test_reserve_idempotent_by_job_id(repo):
    _funded(repo)
    r1 = repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 8, now=NOW)
    r2 = repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 8, now=NOW)
    assert r1.job_id == r2.job_id
    from sqlalchemy import func, select
    from app import models
    n = repo.db.scalar(select(func.count()).select_from(models.Reservation))
    assert n == 1  # not doubled


def test_commit_idempotent_by_step(repo):
    _funded(repo)
    repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 8, now=NOW)
    repo.commit("org1", "job1", "v1:1", "minimax-h3-max", 8, now=NOW)
    repo.commit("org1", "job1", "v1:1", "minimax-h3-max", 8, now=NOW)  # replay
    from app import models
    res = repo.db.get(models.Reservation, "job1")
    assert res.lucas_committed == 160  # counted once


# ── FIFO + tolerance ───────────────────────────────────────────────────────────
def test_commit_consumes_license_before_purchased_fifo(repo):
    repo.grant_license("org1", 300, CYCLE_END)
    repo.add_purchased("org1", 300, usd_paid=3.0)
    # 12 images priced together = ceil(0.067×12×5÷0.01) = 402 Lucas (rounded once, not 12×34)
    repo.reserve("org1", "job1", "image_single", "b", "nano-banana-2", 12, now=NOW)  # 402 reserved
    repo.commit("org1", "job1", "s1", "nano-banana-2", 12, now=NOW)  # 402: spans both lots
    from app import models
    from sqlalchemy import select
    lots = list(repo.db.scalars(select(models.Lot).where(models.Lot.org_id == "org1")
                                .order_by(models.Lot.created_at)))
    lic, pack = lots[0], lots[1]
    assert lic.consumed == 300           # license fully drained first
    assert pack.consumed == 102          # remainder from purchased (402 − 300)


def test_commit_flags_beyond_tolerance(repo):
    _funded(repo)
    repo.reserve("org1", "job1", "image_single", "b", "nano-banana-2", 1, now=NOW)  # 34 reserved
    repo.commit("org1", "job1", "s1", "nano-banana-2", 2, now=NOW)  # 68 > ceil(34*1.1)=38 → flagged
    from app import models
    from sqlalchemy import select
    step = repo.db.scalar(select(models.ReservationStep))
    assert step.flagged_over_tolerance is True


# ── release ────────────────────────────────────────────────────────────────────
def test_release_settled_frees_unspent(repo):
    _funded(repo)
    repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 8, now=NOW)  # 160
    repo.commit("org1", "job1", "s1", "minimax-h3-max", 4, now=NOW)  # 80 real
    assert repo.release("org1", "job1") == "settled"
    # only 80 charged; 80 unspent returned
    detail = repo.balance_detail("org1", NOW)
    assert detail["reserved"] == 0


def test_release_released_when_no_commits(repo):
    _funded(repo)
    repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 8, now=NOW)
    assert repo.release("org1", "job1") == "released"


def test_release_missing_reservation_raises(repo):
    _funded(repo)
    with pytest.raises(ReservationNotFound):
        repo.release("org1", "nope")


# ── insufficient / free actions ────────────────────────────────────────────────
def test_reserve_blocks_when_insufficient(repo):
    repo.grant_license("org1", 100, CYCLE_END)
    with pytest.raises(InsufficientCredits):
        repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 8, now=NOW)  # 160>100


def test_free_action_refused(repo):
    _funded(repo)
    with pytest.raises(FreeActionBilled):
        repo.reserve("org1", "j", "video_scripts_only", "b", "minimax-h3-max", 8, now=NOW)


# ── Gate 1: $100/org video cap, persisted ──────────────────────────────────────
def test_video_cap_blocks_beyond_100(repo):
    _funded(repo)
    for i in range(33):  # 33 × 300 (15s h3max) = 9,900
        repo.reserve("org1", f"j{i}", "video_segment", "b", "minimax-h3-max", 15, now=NOW)
    with pytest.raises(VideoCapExceeded):
        repo.reserve("org1", "j33", "video_segment", "b", "minimax-h3-max", 15, now=NOW)


def test_video_cap_counts_committed_after_release(repo):
    _funded(repo)
    # commit + release a big video job, then verify the committed spend still counts
    repo.reserve("org1", "j0", "video_segment", "b", "minimax-h3-max", 15, now=NOW)  # 300
    repo.commit("org1", "j0", "s1", "minimax-h3-max", 15, now=NOW)  # 300 committed
    repo.release("org1", "j0")
    assert repo.video_spend("org1") == 300  # settled spend still counts toward the cap


def test_video_cap_is_per_org(repo):
    _funded(repo, org="org1")
    _funded(repo, org="org2")
    for i in range(33):
        repo.reserve("org1", f"j{i}", "video_segment", "b", "minimax-h3-max", 15, now=NOW)
    r = repo.reserve("org2", "jA", "video_segment", "b", "minimax-h3-max", 15, now=NOW)
    assert r.lucas_reserved == 300  # org2 unaffected


# ── orphan auto-release ─────────────────────────────────────────────────────────
def test_sweep_expired_auto_releases(repo):
    _funded(repo)
    repo.reserve("org1", "job1", "video_segment", "b", "minimax-h3-max", 8,
                 now=NOW, expected_end_at=NOW + timedelta(minutes=30))
    swept = repo.sweep_expired(now=NOW + timedelta(minutes=31))
    assert swept == 1
    assert repo.available("org1", NOW + timedelta(minutes=31)) == 1_000_000
