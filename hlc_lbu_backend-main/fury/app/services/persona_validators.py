"""Validación de respuestas de agentes para los pipelines de persona.

Este módulo contiene funciones validadoras que se pasan como callback
a la función _run_agent para validar las respuestas de los agentes.

Usage:
    from services.persona_job_runner_service import _run_agent
    from services.persona_validators import validate_persona_data_collector_response

    raw = await _run_agent(
        persona_data_collector,
        f"persona_{id_buyer_persona}_data",
        collector_input,
        validator=validate_persona_data_collector_response,
    )
"""
import json
import re
from typing import Any

from core.validation import ValidationResult


# ----------------------------------------------------------------------
# Validator: PersonaDataCollector
# ----------------------------------------------------------------------

def validate_persona_data_collector_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente PersonaDataCollector.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Tiene la estructura esperada (buyer_persona, product, etc.)
    - Los datos requeridos están presentes
    
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
        # Limpiar markdown fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {e}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_INVALID_JSON")
    
    if not isinstance(parsed, dict):
        errors.append(f"Expected JSON object, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_JSON_NOT_OBJECT")
    
    error_code = None
    
    # 3. Verificar estructura mínima (buyer_persona es requerido)
    if "buyer_persona" not in parsed:
        errors.append("Missing required field: buyer_persona")
        error_code = "ERR_MISSING_BUYER_PERSONA"
        return ValidationResult(is_valid=False, errors=errors, error_code=error_code)
    
    # 4. Verificar buyer_persona tenga datos esenciales
    buyer_persona = parsed.get("buyer_persona")
    if isinstance(buyer_persona, dict):
        # Verificar campos mínimos del buyer_persona
        if not buyer_persona.get("name"):
            warnings.append("buyer_persona missing 'name' field")
        
        # Verificar que tenga al menos algunos datos útiles
        has_useful_data = any([
            buyer_persona.get("story"),
            buyer_persona.get("pain_points"),
            buyer_persona.get("customer_goal"),
        ])
        if not has_useful_data:
            warnings.append("buyer_persona appears to have minimal data")

    else:
        errors.append("buyer_persona should be an object")
        error_code = "ERR_INVALID_BUYER_PERSONA"
    
    # 5. Advertencias opcionales
    if "product" not in parsed:
        warnings.append("No product information in response (optional)")
    
    # Retornar resultado - permite continuar con advertencias
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
        error_code=error_code,
    )


# ----------------------------------------------------------------------
# Validator: PersonaPrompter
# ----------------------------------------------------------------------

def validate_persona_prompter_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente PersonaPrompter.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Tiene la estructura de prompts (master_prompt, variations)
    - Cada variation tiene los campos requeridos para NanoBanana
    
    Returns:
        ValidationResult con is_valid=True si pasa la validación
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
    
    if not isinstance(parsed, dict):
        errors.append(f"Expected JSON object, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors, error_code="ERR_JSON_NOT_OBJECT")
    
    error_code = None

    # Verificar master_prompt
    if not parsed.get("master_prompt"):
        warnings.append("Missing required field: master_prompt")
    
    # Verificar variations
    variations = parsed.get("variations", [])
    if not variations:
        errors.append("Missing or empty 'variations' array")
        error_code = "ERR_MISSING_VARIATIONS"
        return ValidationResult(is_valid=False, errors=errors, error_code=error_code)
    
    # Verificar estructura de cada variation
    required_variant_fields = ["plan_id", "image_prompts"]
    for i, variation in enumerate(variations):
        if not isinstance(variation, dict):
            errors.append(f"Variation {i} is not a dictionary")
            error_code = "ERR_VARIATION_NOT_DICT"
            continue
            
        for field in required_variant_fields:
            if field not in variation:
                errors.append(f"Variation {i} missing required field: {field}")
                error_code = f"ERR_VARIATION_MISSING_FIELD_{field.upper()}"
                continue
        
        # Verificar image_prompts
        image_prompts = variation.get("image_prompts", [])
        if not image_prompts:
            errors.append(f"Variation {i} has empty image_prompts")
            error_code = "ERR_VARIATION_EMPTY_IMAGE_PROMPTS"
            continue
        
        # Verificar cada image_prompt
        for j, img_prompt in enumerate(image_prompts):
            if not isinstance(img_prompt, dict):
                errors.append(f"image_prompts[{i}][{j}] is not a dictionary")
                error_code = "ERR_IMAGE_PROMPT_NOT_OBJECT"
                continue
                
            if not img_prompt.get("image_prompt"):
                errors.append(f"image_prompts[{i}][{j}] missing 'image_prompt'")
                error_code = "ERR_IMAGE_PROMPT_MISSING_FIELD"
                continue

            if not img_prompt.get("element_id"):
                errors.append(f"image_prompts[{i}][{j}] missing 'element_id'")
                error_code = "ERR_IMAGE_PROMPT_MISSING_ELEMENT_ID"
                continue
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
        error_code=error_code,
    )


# ----------------------------------------------------------------------
# Validator: PersonaAuditor
# ----------------------------------------------------------------------

def validate_persona_auditor_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente PersonaAuditor.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Tiene el campo 'overall_pass' (booleano)
    - Tiene el campo 'issues' (lista)
    
    Returns:
        ValidationResult con is_valid=True si pasa la validación
    """
    errors = []
    warnings = []
    
    if not response or not response.strip():
        errors.append("Empty response from agent")
        return ValidationResult(is_valid=False, errors=errors)
    
    parsed = None
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {e}")
        return ValidationResult(is_valid=False, errors=errors)
    
    if not isinstance(parsed, dict):
        errors.append(f"Expected JSON object, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors)
    
    # Verificar overall_pass
    if "overall_pass" not in parsed:
        errors.append("Missing required field: overall_pass")
    elif not isinstance(parsed["overall_pass"], bool):
        errors.append(f"overall_pass must be boolean, got {type(parsed['overall_pass']).__name__}")
    
    # Verificar issues
    if "issues" not in parsed:
        warnings.append("Missing optional field: issues")
    elif not isinstance(parsed["issues"], list):
        errors.append(f"issues must be a list, got {type(parsed['issues']).__name__}")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
    )


# ----------------------------------------------------------------------
# Validator: EditPrompter
# ----------------------------------------------------------------------

def validate_edit_prompter_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente EditPrompter.
    
    Verifica:
    - La respuesta no está vacía
    - Tiene una longitud mínima razonable
    
    Returns:
        ValidationResult con is_valid=True si pasa la validación
    """
    errors = []
    warnings = []
    
    if not response or not response.strip():
        errors.append("Empty response from agent")
        return ValidationResult(is_valid=False, errors=errors)
    
    # Verificar longitud mínima (una descripción debe tener al menos 20 caracteres)
    if len(response.strip()) < 20:
        warnings.append(f"Response seems too short ({len(response)} chars)")
    
    # Verificar que no sea solo JSON
    if response.strip().startswith("{") or response.strip().startswith("["):
        warnings.append("Response appears to be JSON, expected plain text description")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=response.strip() if len(errors) == 0 else None,
    )


# ----------------------------------------------------------------------
# Validator: PersonaVariantsPrompter
# ----------------------------------------------------------------------

def validate_persona_variants_prompter_response(response: str) -> ValidationResult:
    """Valida la respuesta del agente PersonaVariantsPrompter.
    
    Verifica:
    - La respuesta contiene JSON válido
    - Tiene exactamente 5 variantes
    - Cada variante tiene el campo variant_type válido
    
    Returns:
        ValidationResult con is_valid=True si pasa la validación
    """
    errors = []
    warnings = []
    
    VALID_VARIANT_TYPES = {"Frontal", "Side Face", "Expression", "Full Body", "Outfit"}
    
    if not response or not response.strip():
        errors.append("Empty response from agent")
        return ValidationResult(is_valid=False, errors=errors)
    
    parsed = None
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in response: {e}")
        return ValidationResult(is_valid=False, errors=errors)
    
    if not isinstance(parsed, dict):
        errors.append(f"Expected JSON object, got {type(parsed).__name__}")
        return ValidationResult(is_valid=False, errors=errors)
    
    # Verificar master_prompt
    if not parsed.get("master_prompt"):
        warnings.append("Missing optional field: master_prompt")
    
    # Verificar variants. The agent instruction + downstream pipeline both use the
    # "variants" key; accept the legacy "variations" spelling too so a model emitting
    # either passes (gpt-5.4 emitted "variations", gemini-2.5-pro emits "variants").
    variations = parsed.get("variants") or parsed.get("variations") or []
    if not variations:
        errors.append("Missing or empty 'variants' array")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    if len(variations) != 5:
        warnings.append(f"Expected 5 variations, got {len(variations)}")
    
    # Verificar que tenga los 5 tipos de variante
    variant_types_found = set()
    for i, variation in enumerate(variations):
        if not isinstance(variation, dict):
            errors.append(f"Variation {i} is not a dictionary")
            continue
            
        variant_type = variation.get("variant_type", "")
        if variant_type:
            variant_types_found.add(variant_type)
        
        # Verificar campos requeridos para NanoBanana
        if "plan_id" not in variation:
            errors.append(f"Variation {i} missing 'plan_id'")
        if "image_prompts" not in variation:
            errors.append(f"Variation {i} missing 'image_prompts'")
    
    # Verificar que estén los tipos de variante esperados
    missing_types = VALID_VARIANT_TYPES - variant_types_found
    if missing_types:
        warnings.append(f"Missing variant types: {missing_types}")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        data=parsed if len(errors) == 0 else None,
    )