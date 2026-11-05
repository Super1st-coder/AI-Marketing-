"""API endpoints for Vertex AI Agent Engine Tools."""
from fastapi import APIRouter, Depends
from typing import Any, List

from core.auth import verify_oidc_token
from agents.tools import campaign_tools

router = APIRouter()


@router.get("/adset_context/{id_adset}", summary="Get Adset Context")
async def get_adset_context(id_adset: int, _: dict = Depends(verify_oidc_token)) -> dict[str, Any]:
    """Retrieve full Ad Set context for the data collector agent."""
    return await campaign_tools.get_adset_context(id_adset)

@router.get("/brand_context/{brand_id}", summary="Get Brand Context")
async def get_brand_context(brand_id: str, _: dict = Depends(verify_oidc_token)) -> dict[str, Any]:
    """Retrieve brand guidelines."""
    return await campaign_tools.get_brand_context(brand_id)

@router.get("/products_by_brand/{brand_id}", summary="Get Products by Brand")
async def get_products_by_brand(brand_id: str, _: dict = Depends(verify_oidc_token)) -> dict[str, Any]:
    """List all products for a brand."""
    return await campaign_tools.get_products_by_brand(brand_id)

@router.get("/product_context/{brand_id}/{product_id}", summary="Get Product Context")
async def get_product_context(brand_id: str, product_id: str, _: dict = Depends(verify_oidc_token)) -> dict[str, Any]:
    """Retrieve full product details."""
    return await campaign_tools.get_product_context(brand_id, product_id)

@router.get("/template_context/{project_id}", summary="Get Template Context")
async def get_template_context(project_id: str, _: dict = Depends(verify_oidc_token)) -> dict[str, Any]:
    """Retrieve Abyssale templates for a project."""
    return await campaign_tools.get_template_context(project_id)

@router.get("/template_definition/{template_id}", summary="Get Template Definition")
async def get_a_template_definition(template_id: str, _: dict = Depends(verify_oidc_token)) -> dict[str, Any]:
    """Retrieve a single template definition."""
    return await campaign_tools.get_a_template_definition(template_id)

@router.get("/ctas", summary="Get CTAs")
async def get_ctas(_: dict = Depends(verify_oidc_token)) -> List[str]:
    """Retrieve valid CTA options."""
    return await campaign_tools.get_ctas()

@router.get("/audience_context/{id_adset}", summary="Get Audience Context")
async def get_audience_context(id_adset: str, _: dict = Depends(verify_oidc_token)) -> dict[str, Any]:
    """Retrieve audience segments for an adset."""
    return await campaign_tools.get_audience_context(id_adset)
