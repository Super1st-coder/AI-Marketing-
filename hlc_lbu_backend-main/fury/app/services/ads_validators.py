"""Validación de respuestas de agentes para el pipeline job_runner_service.

Este módulo contiene funciones validadoras que se pasan como callback
a la función _run_agent para validar las respuestas de los agentes
en el pipeline de 7-agentes.

Usage:
    from services.job_runner_service import _run_agent
    from services.job_validators import validate_estratega_response

    strat_raw = await _run_agent(
        estratega_agent,
        f"adset_{id_adset}_ad_{ad_id}_strat",
        strat_input,
        validator=validate_estratega_response,
    )
"""
import json
import re
from typing import Any

from core.logging import get_logger
from core.validation import ValidationResult

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Validator: Estratega
# ----------------------------------------------------------------------

def validate_estratega_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente Estratega.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Tiene la estructura de estrategias (array de planes)
    - Cada plan tiene los campos requeridos
    
    Returns:
        ValidationResult con is_valid=True si pasa la validación
    """
    errors = []
    warnings = []
    
    # 1. Verificar que no esté vacía
    if not response or not response.strip():
        errors.append("Empty response from agent")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_EMPTY_RESPONSE")
    
    # 2. Intentar parsear JSON
    parsed = None
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {e}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_JSON")
    
    # Espera un array de planes
    if isinstance(parsed, dict):
        # Si es un dict, convertir a array
        parsed = [parsed]
    
    if not isinstance(parsed, list):
        errors.append(f"Expected array of plans, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_STRUCTURE")
    
    if len(parsed) == 0:
        errors.append("Empty array of plans")
        return ValidationResult(is_valid=True, errors=errors, warnings=warnings, data=parsed, error_code="ERR_EMPTY_PLANS")
    
    error_code = None

    # Verificar cada plan
    required_fields = ["id", "template_id"]
    for i, plan in enumerate(parsed):
        if not isinstance(plan, dict):
            errors.append(f"Plan {i} is not a dictionary")
            error_code = "ERR_PLAN_NOT_DICT"
            continue
            
        # Verificar campos esenciales y que no sean null
        for field in required_fields:
            if field not in plan or not plan[field]:
                errors.append(f"Plan {i} missing required field: {field}")
                error_code = f"ERR_PLAN_MISSING_{field.upper()}"

        # Validar tipo de id
        if "id" in plan and not isinstance(plan["id"], str):
            errors.append(f"Plan {i} field 'id' must be a string, got {type(plan['id']).__name__}")
            error_code = "ERR_PLAN_INVALID_TYPE_ID"

        # Validar tipo de template_id (puede ser string o null)
        if "template_id" in plan and plan["template_id"] is not None and not isinstance(plan["template_id"], str):
            errors.append(f"Plan {i} field 'template_id' must be string or null, got {type(plan['template_id']).__name__}")
            error_code = "ERR_PLAN_INVALID_TYPE_TEMPLATE_ID"
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
        error_code=error_code
    )


# ----------------------------------------------------------------------
# Validator: Copywriter
# ----------------------------------------------------------------------

def validate_copywriter_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente Copywriter.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Tiene la estructura de copies (array de copias)
    - Cada copy tiene los campos requeridos
    
    Returns:
        ValidationResult con is_valid=True si pasa la validación
    """
    errors = []
    warnings = []
    
    # 1. Verificar que no esté vacía
    if not response or not response.strip():
        errors.append("Empty response from agent")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_EMPTY_RESPONSE")
    
    # 2. Intentar parsear JSON
    parsed = None
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {e}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_JSON")
    
    # Espera un array de copias
    if isinstance(parsed, dict):
        parsed = [parsed]
    
    if not isinstance(parsed, list):
        errors.append(f"Expected array of copies, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_STRUCTURE")
    
    if len(parsed) == 0:
        errors.append("Empty array of copies")
        return ValidationResult(is_valid=True, errors=errors, warnings=warnings, data=parsed, error_code="ERR_EMPTY_COPIES")
    
    error_code = None

    # Verificar cada copy
    required_fields = ["plan_id", "template_id", "headline", "primary_text", "description", "cta", "template_elements"]
    for i, copy in enumerate(parsed):
        if not isinstance(copy, dict):
            errors.append(f"Copy {i} is not a dictionary")
            error_code = "ERR_COPY_NOT_DICT"
            continue
            
        # Verificar campos esenciales
        for field in required_fields:
            if field not in copy or not copy[field]:
                errors.append(f"Copy {i} missing required field: {field}")
                error_code = f"ERR_COPY_MISSING_{field.upper()}"
                continue

        # Validar tipos de campos esenciales
        if "plan_id" in copy and not isinstance(copy["plan_id"], str):
            errors.append(f"Copy {i} field 'plan_id' must be a string, got {type(copy['plan_id']).__name__}")
            error_code = "ERR_COPY_INVALID_TYPE_PLAN_ID"

        if "template_id" in copy and copy["template_id"] is not None and not isinstance(copy["template_id"], str):
            errors.append(f"Copy {i} field 'template_id' must be string or null, got {type(copy['template_id']).__name__}")
            error_code = "ERR_COPY_INVALID_TYPE_TEMPLATE_ID"

        # Validar que template_elements sea un array
        if "template_elements" in copy and not isinstance(copy["template_elements"], list):
            errors.append(f"Copy {i} field 'template_elements' must be an array, got {type(copy['template_elements']).__name__}")
            error_code = "ERR_COPY_INVALID_TYPE_TEMPLATE_ELEMENTS"

        # Validar el campo headline sea un array
        if "headline" in copy and not isinstance(copy["headline"], list):
            errors.append(f"Copy {i} field 'headline' must be an array, got {type(copy['headline']).__name__}")
            error_code = "ERR_COPY_INVALID_TYPE_HEADLINE"

        # Validar el campo primary_text sea un array
        if "primary_text" in copy and not isinstance(copy["primary_text"], list):
            errors.append(f"Copy {i} field 'primary_text' must be an array, got {type(copy['primary_text']).__name__}")
            error_code = "ERR_COPY_INVALID_TYPE_PRIMARY_TEXT"

        # Validar el campo description sea un array
        if "description" in copy and not isinstance(copy["description"], list):
            errors.append(f"Copy {i} field 'description' must be an array, got {type(copy['description']).__name__}")
            error_code = "ERR_COPY_INVALID_TYPE_DESCRIPTION"

        # Validar el campo cta sea un array
        if "cta" in copy and not isinstance(copy["cta"], list):
            errors.append(f"Copy {i} field 'cta' must be an array, got {type(copy['cta']).__name__}")
            error_code = "ERR_COPY_INVALID_TYPE_CTA"
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
        error_code=error_code
    )


# ----------------------------------------------------------------------
# Validator: Save Ads
# ----------------------------------------------------------------------

def validate_save_ads_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente Save Ads.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Retorna un array de objetos
    - Cada objeto tiene plan_id, template_id, saved, ad_id
    - saved es booleano
    - ad_id es string o null
    """
    errors = []
    warnings = []

    if not response or not response.strip():
        errors.append("Empty response from agent")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_EMPTY_RESPONSE")

    parsed = None
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {e}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_JSON")

    if isinstance(parsed, dict):
        parsed = [parsed]

    if not isinstance(parsed, list):
        errors.append(f"Expected array of save_ads results, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_STRUCTURE")

    if len(parsed) == 0:
        warnings.append("Empty array of save ads results")
        return ValidationResult(is_valid=True, errors=errors, warnings=warnings, data=parsed, error_code="ERR_EMPTY_SAVE_ADS")

    error_code = None
    required_fields = ["plan_id", "template_id", "saved", "ad_id"]

    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            errors.append(f"SaveAds item {i} is not a dictionary")
            error_code = "ERR_SAVE_ADS_ITEM_NOT_DICT"
            continue

        for field in required_fields:
            if field not in item or not item[field]:
                errors.append(f"SaveAds item {i} missing required field: {field}")
                error_code = f"ERR_SAVE_ADS_MISSING_{field.upper()}"

        if "saved" in item and not isinstance(item["saved"], bool):
            errors.append(f"SaveAds item {i} field 'saved' must be boolean, got {type(item['saved']).__name__}")
            error_code = "ERR_SAVE_ADS_INVALID_TYPE_SAVED"

        if not item.get("saved"):
            errors.append(f"SaveAds item {i} was not saved successfully")
            error_code = "ERR_SAVE_ADS_NOT_SAVED"

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
        error_code=error_code
    )


# ----------------------------------------------------------------------
# Validator: Image Prompter
# ----------------------------------------------------------------------

def validate_image_prompter_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente Image Prompter.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Tiene la estructura de image_prompts (array de prompts)
    - Cada prompt tiene los campos requeridos
    
    Returns:
        ValidationResult con is_valid=True si pasa la validación
    """
    errors = []
    warnings = []
    
    # 1. Verificar que no esté vacía
    if not response or not response.strip():
        errors.append("Empty response from agent")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_EMPTY_RESPONSE")
    
    # 2. Intentar parsear JSON
    parsed = None
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {e}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_JSON")
    
    # Espera un array de prompts
    if isinstance(parsed, dict):
        parsed = [parsed]
    
    if not isinstance(parsed, list):
        errors.append(f"Expected array of image prompts, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_STRUCTURE")
    
    if len(parsed) == 0:
        errors.append("Empty array of image prompts")
        return ValidationResult(is_valid=True, errors=errors, warnings=warnings, data=parsed, error_code="ERR_EMPTY_IMAGE_PROMPTS")
    
    error_code = None

    # Verificar cada prompt
    required_fields = ["plan_id", "template_id"]
    for i, prompt in enumerate(parsed):
        if not isinstance(prompt, dict):
            errors.append(f"Prompt {i} is not a dictionary")
            error_code = "ERR_PROMPT_NOT_DICT"
            continue
            
        # Verificar campos esenciales
        for field in required_fields:
             if field not in prompt or not prompt[field]:
                errors.append(f"Prompt {i} missing required field: {field}")
                error_code = f"ERR_PROMPT_MISSING_{field.upper()}"
                continue

        # `image_prompts` es obligatorio pero puede ser [] : el prompt del agente pide una
        # lista vacía cuando la plantilla no tiene elementos de tipo "image" (no hay nada
        # que generar). Se acepta con un warning; null o ausente siguen siendo error.
        if "image_prompts" not in prompt or prompt["image_prompts"] is None:
            errors.append(f"Prompt {i} missing required field: image_prompts")
            error_code = "ERR_PROMPT_MISSING_IMAGE_PROMPTS"
        elif prompt["image_prompts"] == []:
            message = (f"Prompt {i} (plan_id={prompt.get('plan_id')!r}, "
                       f"template_id={prompt.get('template_id')!r}) has an empty image_prompts "
                       f"list: no image will be generated for it")
            warnings.append(message)
            logger.warning(message)
             
        # Validar tipos de campos esenciales
        if "plan_id" in prompt and not isinstance(prompt["plan_id"], str):
            errors.append(f"Prompt {i} field 'plan_id' must be a string, got {type(prompt['plan_id']).__name__}")
            error_code = "ERR_PROMPT_INVALID_TYPE_PLAN_ID"

        if "template_id" in prompt and prompt["template_id"] is not None and not isinstance(prompt["template_id"], str):
            errors.append(f"Prompt {i} field 'template_id' must be string or null, got {type(prompt['template_id']).__name__}")
            error_code = "ERR_PROMPT_INVALID_TYPE_TEMPLATE_ID"

        if prompt.get("image_prompts") is not None and not isinstance(prompt["image_prompts"], list):
            errors.append(f"Prompt {i} field 'image_prompts' must be an array, got {type(prompt['image_prompts']).__name__}")
            error_code = "ERR_PROMPT_INVALID_TYPE_IMAGE_PROMPTS"
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
        error_code=error_code
    )


# ----------------------------------------------------------------------
# Validator: Validador (Validation Agent)
# ----------------------------------------------------------------------

def validate_validador_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente Validador.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Tiene el campo 'overall_pass' (booleano)
    - Tiene el campo 'issues' (lista)
    
    Returns:
        ValidationResult con is_valid=True si pasa la validación
    """
    errors = []
    warnings = []
    
    # 1. Verificar que no esté vacía
    if not response or not response.strip():
        errors.append("Empty response from agent")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_EMPTY_RESPONSE")
    
    # 2. Intentar parsear JSON
    parsed = None
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {e}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_JSON")
    
    if not isinstance(parsed, dict):
        errors.append(f"Expected JSON object, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_STRUCTURE")
    
    error_code = None

    # Verificar overall_pass: presencia y tipo booleano (False es válido, Req 7.11)
    if "overall_pass" not in parsed:
        errors.append("Missing required field: overall_pass")
        error_code = "ERR_MISSING_OVERALL_PASS"
    elif not isinstance(parsed["overall_pass"], bool):
        errors.append(f"overall_pass must be boolean, got {type(parsed['overall_pass']).__name__}")
        error_code = "ERR_INVALID_TYPE_OVERALL_PASS"

    # Verificar subset_to_regenerate: presencia y tipo lista
    if "subset_to_regenerate" not in parsed:
        errors.append("Missing required field: subset_to_regenerate")
        error_code = "ERR_MISSING_SUBSET_TO_REGENERATE"
    elif not isinstance(parsed["subset_to_regenerate"], list):
        errors.append(f"subset_to_regenerate must be a list, got {type(parsed['subset_to_regenerate']).__name__}")
        error_code = "ERR_INVALID_TYPE_SUBSET_TO_REGENERATE"

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
        error_code=error_code
    )


# ----------------------------------------------------------------------
# Validator: Estratega de AdSet (Phase A — Ads Assembly v2)
# ----------------------------------------------------------------------

def validate_estratega_adset_response(response: str) -> ValidationResult:
    """Validate + PARSE the estratega_adset (Phase A) response.

    Expects a JSON array of {index, concept, ...}, one per assigned territory. Parsing
    mirrors the other validators (strip markdown fences -> json.loads). Returns the parsed
    list as `data`, so run_agent hands job_runner a list (not raw text) and
    apply_descriptions can merge concepts by index. Missing concepts are warnings, not
    hard failures — apply_descriptions tolerates gaps and leaves those territories unwritten.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not response or not response.strip():
        return ValidationResult(is_valid=False, errors=["Empty response from agent"], error_code="ERR_EMPTY_RESPONSE")

    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return ValidationResult(is_valid=False, errors=[f"Invalid JSON in response: {e}"], error_code="ERR_INVALID_JSON")

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return ValidationResult(
            is_valid=False,
            errors=[f"Expected array of descriptions, got {type(parsed).__name__}"],
            error_code="ERR_INVALID_STRUCTURE",
        )

    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            warnings.append(f"item {i} is not an object")
        elif not item.get("concept"):
            warnings.append(f"item {i} missing 'concept'")

    return ValidationResult(is_valid=True, errors=errors, warnings=warnings, data=parsed, error_code=None)


# ----------------------------------------------------------------------
# Validator: Ad Variant Image Prompter (edit pipeline)
# ----------------------------------------------------------------------

AD_VARIANT_IMAGE_PROMPT_MAX_CHARS = 2000

# Un único bloque ```json ... ``` (o ``` ... ```) que envuelve toda la respuesta.
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def validate_ad_variant_image_prompter_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente ad_variant_image_prompter (Req 8.5, 8.6).

    Acepta solo un objeto JSON con `image_prompt: str`, no vacío tras strip y de como
    máximo 2000 caracteres (medidos tras strip). Tolera fences ```json``` alrededor
    del objeto, pero no texto libre.
    data = dict parseado con image_prompt ya recortado.
    error_code ∈ {"EMPTY_RESPONSE", "INVALID_JSON", "NOT_AN_OBJECT", "MISSING_FIELD",
                  "INVALID_TYPE", "EMPTY_FIELD", "TOO_LONG"}.
    """
    if not isinstance(response, str) or not response.strip():
        return ValidationResult(is_valid=False, errors=["Empty response from agent"], error_code="EMPTY_RESPONSE")

    text = response.strip()
    fence = _JSON_FENCE_RE.match(text)
    if fence:
        text = fence.group(1)

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        return ValidationResult(is_valid=False, errors=[f"Response is not valid JSON: {e}"], error_code="INVALID_JSON")

    if not isinstance(parsed, dict):
        return ValidationResult(
            is_valid=False,
            errors=[f"Response JSON is not an object (got {type(parsed).__name__})"],
            error_code="NOT_AN_OBJECT",
        )

    if "image_prompt" not in parsed:
        return ValidationResult(is_valid=False, errors=["Missing field 'image_prompt'"], error_code="MISSING_FIELD")

    image_prompt = parsed["image_prompt"]
    if not isinstance(image_prompt, str):
        return ValidationResult(
            is_valid=False,
            errors=[f"'image_prompt' must be a string, got {type(image_prompt).__name__}"],
            error_code="INVALID_TYPE",
        )

    image_prompt = image_prompt.strip()
    if not image_prompt:
        return ValidationResult(is_valid=False, errors=["'image_prompt' is empty"], error_code="EMPTY_FIELD")

    if len(image_prompt) > AD_VARIANT_IMAGE_PROMPT_MAX_CHARS:
        return ValidationResult(
            is_valid=False,
            errors=[f"'image_prompt' exceeds {AD_VARIANT_IMAGE_PROMPT_MAX_CHARS} characters ({len(image_prompt)})"],
            error_code="TOO_LONG",
        )

    data = dict(parsed)
    data["image_prompt"] = image_prompt
    return ValidationResult(is_valid=True, errors=[], warnings=[], data=data, error_code=None)
