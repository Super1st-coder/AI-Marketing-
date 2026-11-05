"""Validation tools — Andromeda Creative Similarity Score.

Checks diversity across 4 dimensions:
  - S_axes:         strategic axes match (hard constraint + weighted)
  - S_text:         Jaccard similarity on copy texts
  - S_image_prompt: lexical similarity on image prompts
  - S_template:     same template_id penalty

S_final = 0.50*S_axes + 0.25*S_text + 0.15*S_image_prompt + 0.10*S_template

Hard fail: count_same_axes(i,j) > 2
Soft fail: S_final >= SOFT_THRESHOLD (default 0.55, configurable per org)
"""
from typing import Any
from core.logging import get_logger

logger = get_logger(__name__)

EJES = ["emocion", "intencion", "visual_dominante", "contexto_uso", "psicologia"]
SOFT_FAIL_THRESHOLD = 0.55

WEIGHTS = {
    "s_axes": 0.50,
    "s_text": 0.25,
    "s_image_prompt": 0.15,
    "s_template": 0.10,
}


def _jaccard(a: str, b: str) -> float:
    """Jaccard similarity over word sets."""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _compute_pair_similarity(ad_i: dict, ad_j: dict) -> dict:
    """Compute Andromeda similarity between two ad proposals."""
    # --- S_axes ---
    same_axes = sum(
        1 for e in EJES
        if ad_i.get("plan", {}).get(e) == ad_j.get("plan", {}).get(e)
    )
    s_axes = same_axes / len(EJES)

    # --- S_text: Jaccard on (headline + cta + description + primary_text) ---
    def _copy_text(ad: dict) -> str:
        """Flatten copy fields into a single string.

        Each of the fields `headline`, `cta`, `description` and `primary_text`
        may be either a single string or a list/tuple of strings (variants).
        This helper normalizes both cases by concatenating all non-empty
        variants with a space separator so the Jaccard similarity runs over
        the union of tokens present in any variant.
        """
        copy = ad.get("copy", {}) or {}

        def _as_list(v):
            if v is None:
                return []
            if isinstance(v, (list, tuple)):
                return [str(x) for x in v if x is not None and str(x).strip() != ""]
            return [str(v)] if str(v).strip() != "" else []

        parts = []
        for key in ("headline", "cta", "description", "primary_text"):
            parts.extend(_as_list(copy.get(key, "")))

        return " ".join(parts)

    s_text = _jaccard(_copy_text(ad_i), _copy_text(ad_j))

    # --- S_image_prompt: Jaccard on image prompts ---
    # s_image_prompt = _jaccard(
    #     ad_i.get("image_prompts", []),
    #     ad_j.get("image_prompts", []),
    # )

    # --- S_template: same template penalty ---
    s_template = float(
        ad_i.get("plan", {}).get("template_id") ==
        ad_j.get("plan", {}).get("template_id")
    )

    s_final = (
        WEIGHTS["s_axes"] * s_axes
        + WEIGHTS["s_text"] * s_text
        # + WEIGHTS["s_image_prompt"] * s_image_prompt
        + WEIGHTS["s_template"] * s_template
    )

    return {
        "same_axes": same_axes,
        "s_axes": round(s_axes, 3),
        "s_text": round(s_text, 3),
        # "s_image_prompt": round(s_image_prompt, 3),
        "s_template": s_template,
        "s_final": round(s_final, 3),
        "hard_fail": same_axes > 2,
        "soft_fail": s_final >= SOFT_FAIL_THRESHOLD,
    }


def check_diversity_and_fidelity(
    proposals: list[dict],
) -> dict[str, Any]:
    """Evaluate all proposal pairs for creative diversity.

    Each proposal in the list must have:
      - plan: { id, emocion, intencion, visual_dominante, contexto_uso, psicologia, template_id }
      - copy: { headline, cta, description, primary_text }
      - image_prompts: list

    Args:
        proposals: List of combined proposal dicts (plan + copy + image_prompts).

    Returns:
        Dict with overall_pass, conflicts list, and subset_to_regenerate (plan_ids).
    """
    threshold = SOFT_FAIL_THRESHOLD

    conflicts = []
    for i in range(len(proposals)):
        for j in range(i + 1, len(proposals)):
            sim = _compute_pair_similarity(proposals[i], proposals[j])
            if sim["hard_fail"] or sim["s_final"] >= threshold:
                conflicts.append({
                    "plan_i": proposals[i].get("plan", {}).get("id", str(i)),
                    "plan_j": proposals[j].get("plan", {}).get("id", str(j)),
                    **sim,
                })

    failing_ids = list(
        {c["plan_i"] for c in conflicts} | {c["plan_j"] for c in conflicts}
    )

    logger.info(
        f"Andromeda validation: {len(conflicts)} conflicts, "
        f"pass={len(conflicts)==0}, failing={failing_ids}"
    )

    return {
        "ok": True,
        "overall_pass": len(conflicts) == 0,
        "conflicts": conflicts,
        "subset_to_regenerate": failing_ids,
        "threshold_used": threshold,
    }
