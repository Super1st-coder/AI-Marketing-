"""LucaCredit billing service — FastAPI app.

Exposes the 4-call contract other modules call (estimate/reserve/commit/release) plus a
balance read for the header credit counter. Every billing route is internal-only
(X-Internal-Key). Each handler is a thin wrapper over CreditsRepository; the rules and
math live in the `lucas` domain core + repository, not here.
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import verify_internal_key
from app.config import settings
from app.database import get_db
from app.repository import (
    CreditsRepository,
    FreeActionBilled,
    ReservationNotFound,
    VideoCapExceeded,
)
from lucas.engine import InsufficientCredits
from lucas.registry import UnpricedModel

# Bump on every deploy so we can confirm which build is live (mirrors Guide's health marker).
BUILD_MARKER = "ledger-core-api-1"

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME,
            "version": settings.APP_VERSION, "build": BUILD_MARKER}


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def ui() -> HTMLResponse:
    """Light demo dashboard (credit counter + usage bar + top-up + try-a-run). Same-origin,
    so it calls the API directly. The page shell is public; its API calls carry the key."""
    path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(path, encoding="utf-8") as f:
        return HTMLResponse(f.read())


_billing = "/api/v1/billing"


@app.post(f"{_billing}/estimate", response_model=schemas.EstimateResponse,
          dependencies=[Depends(verify_internal_key)])
def estimate(req: schemas.EstimateRequest, db: Session = Depends(get_db)):
    """FREE — prices a request in Lucas. Holds nothing, never blocks. Refuses gated models."""
    repo = CreditsRepository(db)
    try:
        lucas = repo.estimate(req.model_id, req.qty)
    except UnpricedModel as e:
        raise HTTPException(status.HTTP_409_CONFLICT, _err("UNPRICED_MODEL", str(e)))
    except (KeyError, ValueError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _err("BAD_REQUEST", str(e)))
    return schemas.EstimateResponse(model_id=req.model_id, qty=req.qty, lucas=lucas)


@app.post(f"{_billing}/reserve", response_model=schemas.ReserveResponse,
          dependencies=[Depends(verify_internal_key)])
def reserve(req: schemas.ReserveRequest, db: Session = Depends(get_db)):
    repo = CreditsRepository(db)
    try:
        res = repo.reserve(req.org_id, req.job_id, req.action_id, req.brand_id,
                           req.model_id, req.qty, expected_end_at=req.expected_end_at)
    except InsufficientCredits as e:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED,
                            _err("INSUFFICIENT_CREDITS", str(e)))
    except VideoCapExceeded as e:
        # LIMIT_REACHED is the code the Video-PRD UI handles (Marco 2026-09-23) — the
        # "Select variants to generate" button turns into "You need X more LUCA · Top Up".
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED,
                            _err("LIMIT_REACHED", str(e)))
    except FreeActionBilled as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _err("FREE_ACTION", str(e)))
    except UnpricedModel as e:
        raise HTTPException(status.HTTP_409_CONFLICT, _err("UNPRICED_MODEL", str(e)))
    except (KeyError, ValueError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _err("BAD_REQUEST", str(e)))
    return schemas.ReserveResponse(job_id=res.job_id, lucas_reserved=res.lucas_reserved,
                                   model_id=res.model_id, model_version=res.model_version,
                                   status=res.status)


@app.post(f"{_billing}/commit", response_model=schemas.CommitResponse,
          dependencies=[Depends(verify_internal_key)])
def commit(req: schemas.CommitRequest, db: Session = Depends(get_db)):
    repo = CreditsRepository(db)
    try:
        repo.commit(req.org_id, req.job_id, req.step_id, req.model_id, req.qty_real)
    except ReservationNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _err("RESERVATION_NOT_FOUND", str(e)))
    except UnpricedModel as e:
        raise HTTPException(status.HTTP_409_CONFLICT, _err("UNPRICED_MODEL", str(e)))
    except InsufficientCredits as e:
        raise HTTPException(status.HTTP_409_CONFLICT, _err("RESERVATION_BYPASSED", str(e)))
    except (KeyError, ValueError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _err("BAD_REQUEST", str(e)))
    res = db.get(models.Reservation, req.job_id)
    return schemas.CommitResponse(job_id=req.job_id, step_id=req.step_id,
                                  lucas_committed=res.lucas_committed)


@app.post(f"{_billing}/release", response_model=schemas.ReleaseResponse,
          dependencies=[Depends(verify_internal_key)])
def release(req: schemas.ReleaseRequest, db: Session = Depends(get_db)):
    repo = CreditsRepository(db)
    try:
        new_status = repo.release(req.org_id, req.job_id, req.reason)
    except ReservationNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _err("RESERVATION_NOT_FOUND", str(e)))
    return schemas.ReleaseResponse(job_id=req.job_id, status=new_status)


@app.get(f"{_billing}/balance/{{org_id}}", response_model=schemas.BalanceResponse,
         dependencies=[Depends(verify_internal_key)])
def balance(org_id: str, db: Session = Depends(get_db)):
    repo = CreditsRepository(db)
    detail = repo.balance_detail(org_id)
    return schemas.BalanceResponse(org_id=org_id, **detail)


@app.get("/api/v1/registry", dependencies=[Depends(verify_internal_key)])
def registry_snapshot(db: Session = Depends(get_db)):
    """Current price table + gated models, read from the DB registry (the runtime source)."""
    from sqlalchemy import select
    rows = db.scalars(select(models.ModelRegistryRow).where(
        models.ModelRegistryRow.is_current.is_(True)))
    sellable, gated = [], {}
    for r in rows:
        if r.sellable:
            sellable.append({"model_id": r.model_id, "provider_cost_usd": r.provider_cost_usd,
                             "unit": r.unit, "version": r.version, "multiplier": r.multiplier})
        else:
            gated[r.model_id] = r.gate_reason
    return {"sellable": sellable, "gated": gated}


@app.post("/api/v1/registry/price", dependencies=[Depends(verify_internal_key)])
def edit_price(req: schemas.PriceEditRequest, db: Session = Depends(get_db)):
    """Edit a price WITHOUT a deploy — supersedes the current row with a new version and
    notifies finance (Marco §4(1)). In-flight jobs keep their frozen version."""
    from app import pricing
    try:
        row = pricing.set_price(
            db, req.model_id, provider_cost_usd=req.provider_cost_usd, multiplier=req.multiplier,
            sellable=req.sellable, gate_reason=req.gate_reason, max_seconds=req.max_seconds,
            verified_at=req.verified_at, edited_by=req.edited_by)
    except pricing.UnknownModel as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _err("UNKNOWN_MODEL", str(e)))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _err("BAD_EDIT", str(e)))
    return {"model_id": row.model_id, "version": row.version,
            "provider_cost_usd": row.provider_cost_usd, "sellable": row.sellable}


@app.post("/api/v1/registry/reconcile", dependencies=[Depends(verify_internal_key)])
def reconcile_prices(req: schemas.ReconcileRequest, db: Session = Depends(get_db)):
    """Drift check: observed cost/unit (from LangFuse) vs registry → >threshold alerts."""
    from app.reconcile import reconcile_report
    return reconcile_report(db, req.observed_cost_usd, req.threshold)
