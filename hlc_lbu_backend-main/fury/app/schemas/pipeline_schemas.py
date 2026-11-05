"""Pipeline Pydantic schemas — variants, jobs, proposals, and webhooks."""
from __future__ import annotations
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

class VariantCreate(BaseModel):
    id_adset: int = Field(0, ge=0, description="Ad Set ID in Strapi")
    n_variants: int = Field(3, ge=1, description="Number of ad variants to generate")
    project_id: Optional[str] = Field(None, description="Override Abyssale Project ID (optional — Estratega selects per plan if omitted)")
    idempotency_key: Optional[str] = Field(None, description="Client idempotency key to prevent duplicate jobs")
    id_ad: Optional[int] = Field(0, ge=0, description="Ad ID in Strapi (optional)")
    custom_prompt: Optional[str] = Field(None, description="Custom prompt to use instead of the default one (optional)")
    add_variant: Optional[bool] = Field(True, description="Whether to add the generated variant to the ad immediately (default: true)")
    id_variant: Optional[list[int]] = Field(None, description="List of variant IDs to update instead of creating new ones (optional)")

    @model_validator(mode="after")
    def _validate_request(self) -> "VariantCreate":
        """Cross-field rules (Req 1.2–1.8, D3). Reads the diversity flag at validation time."""
        from core.config import settings  # lazy: avoids import cycles and honours patching in tests

        errors: list[str] = []
        replace = self.add_variant is not True  # False or explicit null (P8)
        if not self.id_adset:  # omitted (default 0) or 0 — Req 1.6
            errors.append("id_adset: must be greater than 0")
        if self.id_variant and any(v < 1 for v in self.id_variant):  # Req 1.3
            errors.append("id_variant: all values must be >= 1")
        if replace and not self.id_variant:  # Req 1.2
            errors.append("id_variant: required and non-empty when add_variant is false")
        if replace and not self.id_ad:  # Req 1.4
            errors.append("id_ad: required (> 0) when add_variant is false")
        if settings.USE_ADSET_CREATIVE_DIVERSITY and not (self.project_id or "").strip():  # Req 1.8
            errors.append("project_id: required when USE_ADSET_CREATIVE_DIVERSITY is enabled")
        if errors:
            raise ValueError("; ".join(errors))
        return self


# ---------------------------------------------------------------------------
# Job / Variant responses
# ---------------------------------------------------------------------------

class VariantJobResponse(BaseModel):
    ok: int = 1
    data: dict[str, Any]  # { variant_job_id, id_adset, status, created_at }


class JobStatusResponse(BaseModel):
    ok: int = 1
    data: dict[str, Any]  # { id, status, created_at, updated_at, result?, error? }


# ---------------------------------------------------------------------------
# Proposal schemas
# ---------------------------------------------------------------------------

class ProposalSelectBody(BaseModel):
    proposal_id: str


class ProposalOpenEditorResponse(BaseModel):
    ok: int = 1
    data: dict[str, Any]  # { edit_url: str, expires_at: str }


# ---------------------------------------------------------------------------
# Webhook payloads
# ---------------------------------------------------------------------------

class AbyssaleWebhookPayload(BaseModel):
    batch_id: str
    status: str  # "completed" | "failed"
    renders: list[dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None


class AIExpansionWebhookPayload(BaseModel):
    batch_id: str
    status: str
    expanded_renders: list[dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Ad-variant image edit pipeline
# (POST /api/v2/variants/image/edit → services/job_runner_service
#  ._run_edit_ad_variant_image_pipeline)
# ---------------------------------------------------------------------------

class ExpandZoomOption(str, Enum):
    """Expansion / zoom-out option. Value == name (Req 1.8). Case-sensitive."""
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    ZOOM_2X = "ZOOM_2X"
    ZOOM_1_5X = "ZOOM_1_5X"
    ZOOM_1_25X = "ZOOM_1_25X"


class AdVariantImageEditCreate(BaseModel):
    """Edit_Request — payload of POST /variants/image/edit (and /run-local)."""
    brand_id: int = Field(..., ge=1, description="Brand ID in Sinergia")
    campaign_id: int = Field(..., ge=1, description="Campaign ID in Sinergia")
    ad_id: int = Field(..., ge=1, description="Ad ID in Sinergia")
    channel_id: int = Field(..., ge=1, description="Channel ID in Sinergia")
    variant_id: int = Field(..., ge=1, description="Ad variant ID in Sinergia")
    image_name: str = Field(..., min_length=1, max_length=255, description="Name for the uploaded variations")
    id_base_image: str = Field(..., min_length=1, max_length=255, description="ID of the variant's base image")
    n_variations: int = Field(..., ge=1, le=10, description="Number of edited variations to generate (1-10)")
    custom_prompt: Optional[str] = Field(None, max_length=2000, description="Free-text edit instruction (optional)")
    expand_zoom_option: Optional[ExpandZoomOption] = Field(None, description="Expansion / zoom-out option (optional)")

    @field_validator("image_name", "id_base_image", mode="before")
    @classmethod
    def _strip_required(cls, v: Any) -> Any:
        # Strip before min_length/max_length: "   " → "" → 422 (Req 1.7, 1.12).
        return v.strip() if isinstance(v, str) else v

    @field_validator("custom_prompt", mode="before")
    @classmethod
    def _normalize_custom_prompt(cls, v: Any) -> Any:
        # "" or whitespace-only → None (Req 1.12). max_length is measured after stripping.
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @model_validator(mode="after")
    def _require_prompt_or_option(self) -> "AdVariantImageEditCreate":
        if self.custom_prompt is None and self.expand_zoom_option is None:
            raise ValueError("Se requiere custom_prompt, expand_zoom_option o ambos")
        return self


class AdVariantImageEditJobData(BaseModel):
    edit_job_id: str
    status: Literal["RUNNING"] = "RUNNING"
    poll_url: str


class AdVariantImageEditJobResponse(BaseModel):
    ok: int = 1
    data: AdVariantImageEditJobData


class RegisteredVariant(BaseModel):
    """Edited variation successfully uploaded to Sinergia."""
    id: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)


class AdVariantImageEditResult(BaseModel):
    """Final result of the ad-variant image edit pipeline (Req 10.1)."""
    task_id: str
    variant_id: int
    id_base_image: str
    status: Literal["DONE"] = "DONE"
    variations: list[RegisteredVariant] = Field(..., min_length=1)


# Exact key set of AdVariantImageEditResult — used by jobs.py to detect this
# pipeline's result and return it in full (Req 10.7).
AD_VARIANT_IMAGE_EDIT_RESULT_KEYS: frozenset[str] = frozenset(
    {"task_id", "variant_id", "id_base_image", "status", "variations"}
)
