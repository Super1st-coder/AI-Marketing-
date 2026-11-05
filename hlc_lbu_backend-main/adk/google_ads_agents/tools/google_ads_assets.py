"""Ad copy generation helper tools."""


def validate_ad_copy(headlines: list[str], descriptions: list[str]) -> dict:
    """Validate ad copy against Google Ads RSA requirements.
    Checks character limits and provides warnings for common issues.

    Args:
        headlines: List of headline strings to validate.
        descriptions: List of description strings to validate.

    Returns:
        dict: status with validation results, warnings, and character counts.
    """
    errors = []
    warnings = []
    headline_details = []
    description_details = []

    for i, h in enumerate(headlines):
        length = len(h)
        headline_details.append({"index": i, "text": h, "chars": length, "valid": length <= 30})
        if length > 30:
            errors.append(f"Headline {i+1} is {length} chars (max 30): '{h}'")

    for i, d in enumerate(descriptions):
        length = len(d)
        description_details.append({"index": i, "text": d, "chars": length, "valid": length <= 90})
        if length > 90:
            errors.append(f"Description {i+1} is {length} chars (max 90): '{d}'")

    if len(headlines) < 3:
        errors.append(f"Need at least 3 headlines, got {len(headlines)}")
    if len(headlines) > 15:
        warnings.append(f"Max 15 headlines allowed, got {len(headlines)}. Extra will be trimmed.")
    if len(descriptions) < 2:
        errors.append(f"Need at least 2 descriptions, got {len(descriptions)}")
    if len(descriptions) > 4:
        warnings.append(f"Max 4 descriptions allowed, got {len(descriptions)}. Extra will be trimmed.")

    return {
        "status": "success" if not errors else "error",
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "headlines": headline_details,
        "descriptions": description_details,
    }
