"""API tests — the 4-call contract over HTTP, auth, and error-code mapping."""
import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.repository import CreditsRepository
from app.seed import seed_registry

HEAD = {"X-Internal-Key": "test-internal-key"}  # matches conftest


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    seed_registry(db)  # DB registry is the runtime price source
    # fund an org directly so reserve/commit have balance
    CreditsRepository(db).grant_license("org1", 1_000_000,
                                        __import__("datetime").datetime(2026, 11, 2))
    db.close()
    return TestClient(app)


def test_health_is_open(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["build"] == "ledger-core-api-1"


def test_missing_key_returns_structured_forbidden(client):
    r = client.post("/api/v1/billing/estimate", json={"model_id": "minimax-h3-max", "qty": 8})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "FORBIDDEN"   # structured, not FastAPI's plain string


def test_wrong_key_returns_structured_unauthorized(client):
    r = client.post("/api/v1/billing/estimate",
                    json={"model_id": "minimax-h3-max", "qty": 8},
                    headers={"X-Internal-Key": "nope"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"


def test_estimate_prices(client):
    r = client.post("/api/v1/billing/estimate",
                    json={"model_id": "minimax-h3-max", "qty": 8}, headers=HEAD)
    assert r.status_code == 200
    assert r.json()["lucas"] == 160


def test_estimate_gated_model_409(client):
    r = client.post("/api/v1/billing/estimate",
                    json={"model_id": "flux-3", "qty": 8}, headers=HEAD)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "UNPRICED_MODEL"


def test_full_reserve_commit_release_flow(client):
    body = {"org_id": "org1", "job_id": "job1", "action_id": "video_segment",
            "brand_id": "b", "model_id": "minimax-h3-max", "qty": 8}
    r = client.post("/api/v1/billing/reserve", json=body, headers=HEAD)
    assert r.status_code == 200
    assert r.json()["lucas_reserved"] == 160
    assert r.json()["model_version"] == "1"

    c = client.post("/api/v1/billing/commit",
                    json={"org_id": "org1", "job_id": "job1", "step_id": "s1",
                          "model_id": "minimax-h3-max", "qty_real": 8}, headers=HEAD)
    assert c.status_code == 200
    assert c.json()["lucas_committed"] == 160

    rel = client.post("/api/v1/billing/release",
                      json={"org_id": "org1", "job_id": "job1"}, headers=HEAD)
    assert rel.status_code == 200
    assert rel.json()["status"] == "settled"


def test_reserve_insufficient_returns_402(client):
    # org2 has no funds
    body = {"org_id": "org2", "job_id": "jx", "action_id": "video_segment",
            "brand_id": "b", "model_id": "minimax-h3-max", "qty": 8}
    r = client.post("/api/v1/billing/reserve", json=body, headers=HEAD)
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "INSUFFICIENT_CREDITS"


def test_video_cap_returns_402(client):
    for i in range(33):
        client.post("/api/v1/billing/reserve",
                    json={"org_id": "org1", "job_id": f"j{i}", "action_id": "video_segment",
                          "brand_id": "b", "model_id": "minimax-h3-max", "qty": 15}, headers=HEAD)
    r = client.post("/api/v1/billing/reserve",
                    json={"org_id": "org1", "job_id": "j33", "action_id": "video_segment",
                          "brand_id": "b", "model_id": "minimax-h3-max", "qty": 15}, headers=HEAD)
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "LIMIT_REACHED"


def test_free_action_returns_400(client):
    r = client.post("/api/v1/billing/reserve",
                    json={"org_id": "org1", "job_id": "jf", "action_id": "video_scripts_only",
                          "brand_id": "b", "model_id": "minimax-h3-max", "qty": 8}, headers=HEAD)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "FREE_ACTION"


def test_reserve_is_idempotent_over_http(client):
    body = {"org_id": "org1", "job_id": "jdup", "action_id": "video_segment",
            "brand_id": "b", "model_id": "minimax-h3-max", "qty": 8}
    r1 = client.post("/api/v1/billing/reserve", json=body, headers=HEAD)
    r2 = client.post("/api/v1/billing/reserve", json=body, headers=HEAD)
    assert r1.json()["job_id"] == r2.json()["job_id"]
    b = client.get("/api/v1/billing/balance/org1", headers=HEAD).json()
    assert b["reserved"] == 160  # held once, not twice


def test_balance_endpoint(client):
    b = client.get("/api/v1/billing/balance/org1", headers=HEAD)
    assert b.status_code == 200
    data = b.json()
    assert data["available"] == 1_000_000
    assert data["video_cap"] == 10_000


def test_commit_unknown_reservation_404(client):
    r = client.post("/api/v1/billing/commit",
                    json={"org_id": "org1", "job_id": "ghost", "step_id": "s1",
                          "model_id": "minimax-h3-max", "qty_real": 8}, headers=HEAD)
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "RESERVATION_NOT_FOUND"


def test_registry_snapshot_from_db(client):
    r = client.get("/api/v1/registry", headers=HEAD)
    assert r.status_code == 200
    data = r.json()
    ids = {m["model_id"] for m in data["sellable"]}
    assert "minimax-h3-max" in ids
    assert "flux-3" in data["gated"]  # gated with a reason


def test_edit_price_without_deploy(client):
    r = client.post("/api/v1/registry/price",
                    json={"model_id": "minimax-h3-max", "provider_cost_usd": 0.08,
                          "edited_by": "marco"}, headers=HEAD)
    assert r.status_code == 200
    assert r.json()["version"] == "2"
    # a new estimate immediately reflects the new price — no deploy
    e = client.post("/api/v1/billing/estimate",
                    json={"model_id": "minimax-h3-max", "qty": 8}, headers=HEAD)
    assert e.json()["lucas"] == 320


def test_reconcile_endpoint_flags_drift(client):
    r = client.post("/api/v1/registry/reconcile",
                    json={"observed_cost_usd": {"minimax-h3-max": 0.10}}, headers=HEAD)
    assert r.status_code == 200
    assert r.json()["alert_count"] == 1
    assert r.json()["alerts"][0]["direction"] == "under-charging"
