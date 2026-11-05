"""Campaign tools — ALL Sinergia calls live here.
DataCollector agent uses these; Estratega never calls them directly.
"""
import json
import httpx
from typing import Any
from core.config import settings
from core.logging import get_logger
from core.sinergia_auth import sinergia_auth

logger = get_logger(__name__)

_SINERGIA_CACHE_TTL = 3600  # 1 hour


def _cache_get(key: str):
    """Return cached value or None. Silent on errors."""
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(key: str, value: Any) -> None:
    """Store value in Redis cache. Silent on errors."""
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        r.set(key, json.dumps(value, default=str), ex=_SINERGIA_CACHE_TTL)
    except Exception:
        pass


def _sinergia_headers() -> dict:
    """Base headers without auth — auth is added dynamically."""
    return {"Content-Type": "application/json", "Accept": "application/json"}


async def _sinergia_get(path: str, params: dict | None = None) -> dict:
    """GET from Sinergia with service API key auth."""
    key = await sinergia_auth.get_token()
    headers = {**_sinergia_headers(), "X-Service-API-Key": key}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{settings.SINERGIA_URL}{path}",
            params=params,
            headers=headers,
        )
        r.raise_for_status()
        return r.json()


async def _sinergia_post(path: str, body: dict) -> dict:
    """POST to Sinergia with service API key auth."""
    key = await sinergia_auth.get_token()
    headers = {**_sinergia_headers(), "X-Service-API-Key": key}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{settings.SINERGIA_URL}{path}",
            json=body,
            headers=headers,
        )
        logger.debug(
            f"_sinergia_post path={path} status={r.status_code} request_keys={list(body.keys())}"
        )
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            text = r.text or ""
            logger.error(
                f"_sinergia_post HTTP error path={path} status={r.status_code} response={text[:2000]}"
            )
            raise
        try:
            return r.json()
        except Exception as json_exc:
            text = r.text or ""
            logger.error(
                f"_sinergia_post invalid JSON path={path} status={r.status_code} response={text[:2000]} error={json_exc}"
            )
            raise


# ---------------------------------------------------------------------------
# Tools for data_collector_agent
# ---------------------------------------------------------------------------

async def get_adset_context(id_adset: int) -> dict[str, Any]:
    """Retrieve the full Ad Set from Sinergia including funnel_flow, ads, audiences,
    and experiment_ref.

    Args:
        id_adset: Ad Set ID in Strapi.

    Returns:
        Dict with adset attributes and all populated relations.

    NOTE (Ads Assembly v2 — umbrella exposure): the Phase-A "estratega_adset" step reads
    the umbrella thread from `campaign.umbrella` — specifically `umbrella.title` +
    `umbrella.description` + the consolidated `umbrella.summary` object (big_idea,
    core_message, hook, hero_story, emotional_conflict, solution, …). Shape confirmed
    with Luis; Sinergia is adding this `umbrella` section to `/adset/{id}` (the mock
    already mirrors it). The engine normalizes it via territory_assignment._umbrella_thread
    and tolerates the summary being absent. Ref: Arquitectura del Módulo Ads Assembly — v2,
    §6 (umbrella thread) + §10 (dev handoff gap).
    """
    logger.info(f"get_adset_context: fetching id_adset={id_adset}")
    cache_key = f"fury:sinergia:adset:{id_adset}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info(f"get_adset_context: cache hit id_adset={id_adset}")
        return cached
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/adset/{id_adset}",
        )
        result = {"ok": True, "adset": data.get('data')}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"get_adset_context failed: {e}")
        return {"ok": False, "error": str(e)}


async def get_brand_context(brand_id: str) -> dict[str, Any]:
    """Retrieve brand guidelines from Sinergia: tone of voice, color palette,
    do/donts, visual restrictions.

    Args:
        brand_id: Brand ID in Strapi.

    Returns:
        Dict with brand guidelines attributes.
    """
    cache_key = f"fury:sinergia:brand:{brand_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info(f"get_brand_context: cache hit brand_id={brand_id}")
        return cached
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/brand/{brand_id}",
        )
        result = {"ok": True, "brand": data}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"get_brand_context failed: {e}")
        return {"ok": False, "error": str(e)}


async def get_products_by_brand(brand_id: str) -> dict[str, Any]:
    """List all products registered for a brand in Sinergia.

    Use this when no explicit product_id is available in the adset context.
    The returned list includes each product's id, name, and key attributes —
    pick the most relevant product and then call get_product_context with its id.

    Args:
        brand_id: Brand ID in Strapi.

    Returns:
        Dict with a list of products for the brand.
    """
    try:
        data = await _sinergia_get(
            f"/api/v2/application/hiluca/brand/{brand_id}/product",
        )
        return {"ok": True, "products": data}
    except Exception as e:
        logger.error(f"get_products_by_brand failed: {e}")
        return {"ok": False, "error": str(e)}


# async def get_product_context(brand_id: str, product_id: str) -> dict[str, Any]:
#     """Retrieve full product details from Sinergia: benefits, features, RTBs,
#     price, positioning, and mandatory attributes.

#     Args:
#         brand_id: Brand ID in Strapi (products are scoped to a brand).
#         product_id: Product ID in Strapi (obtain from get_products_by_brand if unknown).

#     Returns:
#         Dict with product attributes.
#     """
#     try:
#         data = await _sinergia_get(
#             f"/api/v2/application/hiluca/brand/{brand_id}/product/{product_id}",
#         )
#         return {"ok": True, "product": data}
#     except Exception as e:
#         logger.error(f"get_product_context failed: {e}")
#         return {"ok": False, "error": str(e)}
    
async def get_product_context(id_product: int) -> dict[str, Any]:
    """Retrieve full product details from Sinergia: benefits, features, RTBs,
    price, positioning, and mandatory attributes.

    Args:
        id_product: Product ID in Strapi.

    Returns:
        Dict with product attributes.
    """
    logger.info(f"get_product_context: fetching id_product={id_product}")
    cache_key = f"fury:sinergia:product:{id_product}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info(f"get_adset_context: cache hit id_product={id_product}")
        return cached
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/product/{id_product}",
        )
        result = {"ok": True, "product": data.get('data')}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"get_adset_context failed: {e}")
        return {"ok": False, "error": str(e)}



async def get_template_context(project_id: str) -> dict[str, Any]:
    """Retrieve Abyssale templates for a media_platform_project_id from Sinergia.

    Args:
        project_id: media_platform_project_id ID in Strapi .

    Returns:
        Dict with list of available templates and their layer schemas.
    """
    logger.info(f"get_template_context: fetching project_id={project_id}")
    cache_key = f"fury:sinergia:templates:{project_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info(f"get_template_context: cache hit project_id={project_id}")
        return cached
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/media_platform/{project_id}/templates",
        )
        result = {"ok": True, "templates": data.get('data')}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"get_template_context failed: {e}")
        return {"ok": False, "error": str(e)}


async def get_a_template_definition(template_id: str) -> dict[str, Any]:
    """Retrieve a single Abyssale template definition by its ID.

    Args:
        template_id: Template UUID.

    Returns:
        Dict with template elements, formats, and metadata.
    """
    logger.info(f"get_a_template_definition: fetching template_id={template_id}")
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/template/{template_id}",
        )
        return {"ok": True, "template": data.get('data')}
    except Exception as e:
        logger.error(f"get_a_template_definition failed: {e}")
        return {"ok": False, "error": str(e)}


async def get_image_from_library(product_id: str) -> list[str]:
    """Retrieve product image URLs from the Sinergia image library.

    Args:
        product_id: Product ID in Strapi.

    Returns:
        List of image URLs for the product.
    """
    logger.info(f"get_image_from_library: fetching product_id={product_id}")
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/product/{product_id}/images",
        )
        images = data.get("data", [])
        logger.info(f"get_image_from_library: found {len(images)} images")
        return [img.get("url") for img in images if img.get("url")]
    except Exception as e:
        logger.error(f"get_image_from_library failed: {e}")
        return []


async def get_person_main_image(id_buyer_persona: int, image_id: str) -> dict[str, Any]:
    """Retrieve a specific image from the Sinergia library by its ID.

    Args:
        id_buyer_persona: Buyer Persona ID in Strapi.
        image_id: Image UUID in the library.

    Returns:
        Dict with image attributes (url, prompt, etc.).
    """
    logger.info(f"get_person_main_image: fetching image_id={image_id}")
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/buyer_persona/{id_buyer_persona}/image/main/{image_id}",
        )
        logger.info(f"get_person_main_image: found image {image_id}")
        return data.get("data", {})
    except Exception as e:
        logger.error(f"get_person_main_image failed: {e}")
        return {}


async def get_persona_variant_image(id_buyer_persona: int, image_id: str) -> dict[str, Any]:
    """Retrieve a specific image from the Sinergia library by its UUID.

    Args:
        id_buyer_persona: Buyer Persona ID in Strapi.
        image_id: Image UUID in the library.

    Returns:
        Dict with image attributes (url, prompt, etc.).
    """
    logger.info(f"get_image_from_library_by_id: fetching image_id={image_id}")
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/buyer_persona/{id_buyer_persona}/image/variant/{image_id}",
        )
        logger.info(f"get_image_from_library_by_id: found image {image_id}")
        return data.get("data", {})
    except Exception as e:
        logger.error(f"get_image_from_library_by_id failed: {e}")
        return {}


async def save_ads(id_adset: int, id_ad: int, payloads: list[dict]) -> dict[str, Any]:
    """Persist multiple ads to Sinergia for a given ad set in a single call.

    Args:
        id_adset: Ad Set ID in Strapi.
        id_ad: Ad ID in Strapi.
        payloads: List of ad payloads, each with media_template_id, media_elements, etc.

    Returns:
        Dict with ok and the list of created ads.
    """
    try:
        data = await _sinergia_post(
            f"/api/v2/service/hiluca/adset/{id_adset}/ads",
            {'ad_id': id_ad, 'ads': payloads},
        )
        return {"ok": True, "ads": data}
    except Exception as e:
        logger.error(f"save_ads failed: {e}")
        return {"ok": False, "error": str(e)}


async def get_ctas() -> list[str]:
    """Retrieve the list of valid CTA options from Sinergia.

    Returns:
        List of CTA strings.
    """
    try:
        data = await _sinergia_get(
            "/api/v2/service/hiluca/cta",
        )
        ctas = data.get("data", [])
        logger.info(f"get_ctas: found {len(ctas)} ctas")
        return ctas
    except Exception as e:
        logger.error(f"get_ctas failed: {e}")
        return []


async def update_ad_channel_with_batch_id(ad_id: int, batch_id: str, image_ids: list[dict]) -> bool:
    """Update the ad channel in Sinergia with the Abyssale batch ID for tracking.

    Args:
        ad_id: Ad ID in Strapi.
        batch_id: Abyssale batch ID to associate with the ad.
        image_ids: List of dicts with image_id and image_name for tracking which images were used in the generation.

    Returns:
        True if update succeeded, False otherwise.
    """
    try:
        await _sinergia_post(
            f"/api/v2/service/hiluca/ad/{ad_id}/update_channel",
            {"batch_id": batch_id, "image_ids": image_ids},
        )
        logger.info(f"update_ad_channel_with_batch_id succeeded for ad_id={ad_id}")
        return True
    except Exception as e:
        logger.error(f"update_ad_channel_with_batch_id failed: {e}")
        return False
    
_MAX_LOGGED_MIME_LEN = 64


def _describe_image_data(value: Any) -> str:
    """Describe an image payload for logs without leaking its content.

    Returns 'data-uri:<mime> len=N' | 'url len=N' | 'text len=N' | 'none'.
    Never includes base64 content or a URL's query string (e.g. signed params).
    """
    if value is None:
        return "none"
    if not isinstance(value, str):
        value = str(value)
    if not value:
        return "none"
    length = len(value)
    if value[:5].lower() == "data:":
        # Without a ',' separator the whole rest may be payload: don't log any of it.
        header = value[5:].split(",", 1)[0].split(";", 1)[0] if "," in value else ""
        # Keep only MIME-safe characters and cap length so no payload slips through.
        mime = "".join(c for c in header if c.isalnum() or c in "/.+-")[:_MAX_LOGGED_MIME_LEN]
        return f"data-uri:{mime or 'unknown'} len={length}"
    if value[:7].lower() == "http://" or value[:8].lower() == "https://":
        return f"url len={length}"
    return f"text len={length}"


async def upload_image_to_library(ad_id: int, image_data: dict) -> str:
    """Upload a generated image to the Sinergia image library and associate it with the ad.

    Args:
        ad_id: Ad ID in Strapi.
        image_data: Dict with image_data (base64 data-URI or URL), image_name, mime_type,
            plan_id and image_prompt (prompt that produced the image; may be "").
            The dict is forwarded unchanged to Sinergia as {"image": image_data}.

    Returns:
        ID of the uploaded image in the library, or empty string on failure.
    """
    try:
        logger.debug(
            f"upload_image_to_library request ad_id={ad_id} image_keys={list(image_data.keys())} "
            f"image_data={_describe_image_data(image_data.get('image_data'))}"
        )
        data = await _sinergia_post(
            f"/api/v2/service/hiluca/ad/{ad_id}/image/upload",
            {"image": image_data},
        )
        logger.info(f"upload_image_to_library succeeded for ad_id={ad_id}, data={json.dumps(data)}")
        image_id = data.get("data", {}).get("image_id", "")
        if not image_id:
            logger.warning(
                f"upload_image_to_library succeeded but no image_id found for ad_id={ad_id}. response={data}"
            )
        return image_id
    except Exception as e:
        logger.error(f"upload_image_to_library failed: {str(e)}")
        return ""
    
async def delete_variants(variant_ids: list[int]) -> bool:
    """Delete generated variants from Sinergia when the user rejects them.

    Args:
        variant_ids: List of variant IDs to delete.
    Returns:
        True if deletion succeeded, False otherwise.
    """
    try:
        await _sinergia_post(
            f"/api/v2/service/hiluca/variants/delete",
            {"variant_ids": variant_ids},
        )
        logger.info(f"delete_variants succeeded for variant_ids={variant_ids}")
        return True
    except Exception as e:
        logger.error(f"delete_variants failed: {e}")
        return False

async def get_audience_context(id_adset: str) -> dict[str, Any]:
    """Retrieve audience segments and psychographic insights for an Ad Set from Sinergia.

    Args:
        id_adset: Ad Set ID — audiences are filtered by ad_set_ref.

    Returns:
        Dict with audience list and insights.
    """
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/adset/{id_adset}/audiences",
        )
        return {"ok": True, "audiences": data}
    except Exception as e:
        logger.error(f"get_audience_context failed: {e}")
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Tools for persona_data_collector_agent
# ---------------------------------------------------------------------------

async def get_buyer_persona_context(id_buyer_persona: int) -> dict[str, Any]:
    """Retrieve full buyer persona profile from Sinergia.

    Includes demographics (name, age_range, gender, hometown), psychographics,
    lifestyle descriptors, goals, pain points, fears, visual archetype, and
    the persona story — everything needed to generate a photorealistic portrait.

    Args:
        id_buyer_persona: Buyer Persona ID in Strapi.

    Returns:
        Dict with buyer persona attributes.
    """
    logger.info(f"get_buyer_persona_context: fetching id={id_buyer_persona}")
    cache_key = f"fury:sinergia:buyer_persona:{id_buyer_persona}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info(f"get_buyer_persona_context: cache hit id={id_buyer_persona}")
        return cached
    try:
        data = await _sinergia_get(
            f"/api/v2/service/hiluca/buyer_persona/{id_buyer_persona}",
        )
        result = {"ok": True, "buyer_persona": data.get("data")}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"get_buyer_persona_context failed: {e}")
        return {"ok": False, "error": str(e)}


async def upload_persona_main_image(persona_id: int, image_data: dict) -> str:
    """Upload a generated persona image to the Sinergia library.

    Args:
        persona_id: Buyer Persona ID in Strapi.
        image_data: Dict with image_data (base64 data-URI), image_name, mime_type, and variation_id.

    Returns:
        ID of the uploaded image in the library, or empty string on failure.
    """
    try:
        data = await _sinergia_post(
            f"/api/v2/service/hiluca/buyer_persona/{persona_id}/image/upload",
            image_data,
        )
        image_id = data.get("data", {}).get("image_id", "")
        logger.info(f"upload_persona_image succeeded for persona_id={persona_id}, image_id={image_id}")
        return image_id
    except Exception as e:
        logger.error(f"upload_persona_image failed for persona_id={persona_id}: {e}")
        return ""


async def upload_persona_image_variant(persona_id: int, image_base_id: str, image_data: dict, label: str) -> str:
    """Upload a generated persona image variant to the Sinergia library.

    Args:
        persona_id: Buyer Persona ID in Strapi.
        image_base_id: UUID of main image this variant is associated with.
        image_data: Dict with image_data (base64 data-URI), image_name, mime_type, and image_prompt.
        label: Variant label (e.g., 'frontal', 'side_face', 'expression')

    Returns:
        ID of the uploaded image in the library, or empty string on failure.
    """
    try:
        data = await _sinergia_post(
            f"/api/v2/service/hiluca/buyer_persona/{persona_id}/image/{image_base_id}/variant/upload",
            {'image': image_data, 'label': label},
        )
        image_id = data.get("data", {}).get("image_id", "")
        logger.info(f"upload_persona_image succeeded for persona_id={persona_id}, image_id={image_id}")
        return image_id
    except Exception as e:
        logger.error(f"upload_persona_image failed for persona_id={persona_id}: {e}")
        return ""


# ---------------------------------------------------------------------------
# Ad variant image edit pipeline (Req 4, 9)
# ---------------------------------------------------------------------------

def _ad_variant_base_path(
    brand_id: int, campaign_id: int, ad_id: int, channel_id: int, variant_id: int,
) -> str:
    """Base path of the Sinergia service routes for an ad variant."""
    return (
        f"/api/v2/service/hiluca/brand/{brand_id}/campaign/{campaign_id}"
        f"/ad/{ad_id}/channel/{channel_id}/variant/{variant_id}"
    )


def _unwrap_sinergia_body(body: Any, path: str) -> dict:
    """Return the ``data`` envelope if present, else the body itself.

    Raises:
        ValueError: if the body (or its ``data`` envelope) is not a dict.
    """
    if not isinstance(body, dict):
        raise ValueError(f"Sinergia response is not a JSON object path={path}")
    data = body.get("data", body)
    if not isinstance(data, dict):
        raise ValueError(f"Sinergia response 'data' is not a JSON object path={path}")
    return data


def _as_str(value: Any) -> str:
    """Absent/None → ""; any other value → str(value)."""
    return "" if value is None else str(value)


async def get_ad_variant_image(
    brand_id: int, campaign_id: int, ad_id: int, channel_id: int, variant_id: int,
    image_name: str, id_base_image: str,
) -> dict[str, Any]:
    """GET {base}/image/{id_base_image} vía _sinergia_get (X-Service-API-Key, timeout 15 s).

    Returns: exactamente {"id": str, "url": str, "prompt": str}, tomados de `data`
    (o del cuerpo si no hay sobre). Campos ausentes/null → "" (prompt siempre str).
    Raises: httpx.HTTPError / ValueError (cuerpo no dict). No captura: Req 4.4.
    `image_name` se acepta por paridad de firma con el contrato; no se envía.
    """
    path = (
        f"{_ad_variant_base_path(brand_id, campaign_id, ad_id, channel_id, variant_id)}"
        f"/image/{id_base_image}"
    )
    logger.info(
        f"get_ad_variant_image: fetching path={path} variant_id={variant_id} "
        f"id_base_image={id_base_image}"
    )
    body = await _sinergia_get(path)
    data = _unwrap_sinergia_body(body, path)
    result = {
        "id": _as_str(data.get("id")),
        "url": _as_str(data.get("url")),
        "prompt": _as_str(data.get("prompt")),
    }
    logger.info(
        f"get_ad_variant_image: found image path={path} variant_id={variant_id} "
        f"id={result['id']}"
    )
    return result
