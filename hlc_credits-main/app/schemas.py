"""Pydantic request/response models for the billing API (the 4-call contract + balance)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EstimateRequest(BaseModel):
    model_id: str
    qty: float = Field(gt=0, description="units: video seconds / images / 1k tokens / 1k chars")


class EstimateResponse(BaseModel):
    model_id: str
    qty: float
    lucas: int


class ReserveRequest(BaseModel):
    org_id: str
    job_id: str
    action_id: str
    brand_id: str
    model_id: str
    qty: float = Field(gt=0)
    expected_end_at: Optional[datetime] = None


class ReserveResponse(BaseModel):
    job_id: str
    lucas_reserved: int
    model_id: str
    model_version: str
    status: str


class CommitRequest(BaseModel):
    org_id: str
    job_id: str
    step_id: str
    model_id: str
    qty_real: float = Field(gt=0)


class CommitResponse(BaseModel):
    job_id: str
    step_id: str
    lucas_committed: int


class ReleaseRequest(BaseModel):
    org_id: str
    job_id: str
    reason: str = "done"


class ReleaseResponse(BaseModel):
    job_id: str
    status: str


class BalanceResponse(BaseModel):
    org_id: str
    available: int
    license: int
    purchased: int
    reserved: int
    video_spend: int
    video_cap: int
    used: int = 0
    granted: int = 0
    usage_pct: float = 0.0
    topup_url: Optional[str] = None


class PriceEditRequest(BaseModel):
    model_id: str
    provider_cost_usd: Optional[float] = None
    multiplier: Optional[float] = None
    sellable: Optional[bool] = None
    gate_reason: Optional[str] = None
    max_seconds: Optional[int] = None
    verified_at: Optional[str] = None
    edited_by: str = "admin"


class ReconcileRequest(BaseModel):
    observed_cost_usd: dict[str, float] = Field(
        description="model_id -> real USD/unit observed (from LangFuse)")
    threshold: float = Field(default=0.10, gt=0, description="fractional deviation to alert on")
