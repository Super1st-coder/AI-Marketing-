"""Persona Image Generation — Pydantic schemas."""
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

class PersonaImageCreate(BaseModel):
    id_buyer_persona: int = Field(..., ge=1, description="Sinergia Buyer Persona ID")
    n_variations: int = Field(4, ge=1, le=10, description="Number of image variations to generate")
    photography_effect: Optional[Literal["Natural", "Flash", "Studio", "Dramatic", "Golden Hour", "Volumetric", "Chiaroscuro", "Back Light", "Hardlight", "Indoor Light", "Sepia", "Black and White"]] = Field(
        "Natural",
        description=(
            "Photography lighting / mood effect applied to every variation. "
            "natural=golden hour candid, flash=street/editorial flash, "
            "studio=3-point clean backdrop, dramatic=chiaroscuro cinematic."
        ),
    )
    id_product: Optional[int] = Field(
        None,
        ge=1,
        description=(
            "Optional Sinergia Product ID. When provided the pipeline will extract product context "
            "(name, benefits, features, RTBs, images)."
        ),
    )
    custom_prompt: Optional[str] = Field(
        None,
        description="Optional free-text directive appended to the PersonaPrompter instruction.",
    )
    id_base_image: Optional[str] = Field(
        None,
        description="UUID of the base image in the library to edit.",
    )
    reference_images: Optional[list[str]] = Field(
        None,
        description="Optional list of binary image URLs for external reference.",
    )
    label: Optional[str] = Field(
        None,
        description="Optional label for the variant (used in the UI).",
    )
    visual_style: Optional[str] = Field(
        None,
        description="Optional visual style descriptor (e.g. 'Natural', 'Studio shot', 'Cartoon fun').",
    )


# ---------------------------------------------------------------------------
# Job response
# ---------------------------------------------------------------------------

class PersonaImageJobResponse(BaseModel):
    ok: int = 1
    data: dict[str, Any]  # { task_id, id_buyer_persona, n_variations, status, poll_url }


# ---------------------------------------------------------------------------
# Result payload (stored in Celery backend, returned by GET /jobs/{task_id})
# ---------------------------------------------------------------------------

class PersonaVariation(BaseModel):
    variation_id: str
    diversity_axes: dict[str, str]
    image_prompt: str
    image_url: Optional[str] = None     # base64 data-URI while no CDN upload
    image_id: Optional[str] = None      # Sinergia library ID after upload
    image_mime_type: Optional[str] = None


class PersonaImageResult(BaseModel):
    task_id: str
    id_buyer_persona: int
    photography_effect: str
    master_prompt: str
    variations: list[PersonaVariation]
    status: str = "DONE"
