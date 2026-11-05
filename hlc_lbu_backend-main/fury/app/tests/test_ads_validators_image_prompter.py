"""`validate_image_prompter_response`: `image_prompts` may be [] (template without image
elements, as the agent's prompt asks), but it must be present and a list.

Run with:
    PYTHONPATH=. pytest tests/test_ads_validators_image_prompter.py
"""
import json

import pytest

from services.ads_validators import validate_image_prompter_response


def _item(**overrides):
    item = {"plan_id": "plan_1", "template_id": "tpl-1",
            "image_prompts": [{"element_id": "img", "image_prompt": "x"}]}
    item.update(overrides)
    return item


def test_non_empty_image_prompts_is_valid_without_warnings():
    result = validate_image_prompter_response(json.dumps([_item()]))
    assert result.is_valid and result.warnings == []


def test_empty_image_prompts_is_valid_with_warning():
    items = [_item(), _item(plan_id="plan_2", image_prompts=[])]
    result = validate_image_prompter_response(json.dumps(items))
    assert result.is_valid, result.errors
    assert result.data == items
    assert len(result.warnings) == 1 and "plan_2" in result.warnings[0]


@pytest.mark.parametrize("item", [
    {"plan_id": "plan_1", "template_id": "tpl-1"},                         # absent
    _item(image_prompts=None),                                             # null
])
def test_missing_image_prompts_is_still_an_error(item):
    result = validate_image_prompter_response(json.dumps([item]))
    assert not result.is_valid
    assert result.error_code == "ERR_PROMPT_MISSING_IMAGE_PROMPTS"


@pytest.mark.parametrize("value", ["a prompt", 3])
def test_non_list_image_prompts_is_an_error(value):
    result = validate_image_prompter_response(json.dumps([_item(image_prompts=value)]))
    assert not result.is_valid
    assert result.error_code == "ERR_PROMPT_INVALID_TYPE_IMAGE_PROMPTS"


@pytest.mark.parametrize("field", ["plan_id", "template_id"])
def test_other_required_fields_unchanged(field):
    result = validate_image_prompter_response(json.dumps([_item(**{field: ""})]))
    assert not result.is_valid
    assert result.error_code == f"ERR_PROMPT_MISSING_{field.upper()}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
