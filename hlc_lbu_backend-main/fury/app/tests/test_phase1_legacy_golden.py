"""Golden regression test for the Legacy_Path of `_run_phase1` (Req 2.2, 2.7, 12.13).

With USE_ADSET_CREATIVE_DIVERSITY set to False (or absent) the sequence of
`(agent_name, message)` sent through `_run_agent` must stay byte-for-byte equal
to the reference below, which was recorded from the code BEFORE the
adset-creative-diversity change, for the same mock Adset_Context and the same
fixed FakeRunAgent responses. Do NOT update the reference to make a change pass:
a diff here means the Legacy_Path changed.

P15 (Req 15.15, 12.36): the Legacy_Path never uses the Image_Elements helpers
(`check_image_elements`, `template_image_elements`, `filter_image_prompts` are
replaced by fakes that fail if called) and calls `get_a_template_definition`
once per copy, only from `_build_save_ads_payloads` (no job cache).

Run:  PYTHONPATH=. env/bin/python -m pytest tests/test_phase1_legacy_golden.py
  or: PYTHONPATH=. env/bin/python -m tests.test_phase1_legacy_golden
"""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from typing import Any, Iterator

import pytest

from tests._diversity_pipeline_fakes import (
    COPYWRITER,
    DEFAULT_TASK_ID,
    ESTRATEGA,
    IMAGE_PROMPTER,
    VALIDADOR,
    FakeGetATemplateDefinition,
    FakeRunAgent,
    make_adset_context,
    patched_diversity_pipeline,
    run_phase1,
)

# ---------------------------------------------------------------------------
# Fixed inputs
# ---------------------------------------------------------------------------

ID_ADSET = 173
ID_AD = 901  # the mock adset has no `ads` reachable by the Legacy_Path, so id_ad is given
N_VARIANTS = 2  # > 1 so the Validador step runs

T1 = "f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4"  # mock template "Awareness"
T2 = "612e957c-44f7-4d6c-be98-5ecd8392673d"

PLANS = [
    {"id": "plan_1", "template_id": T1, "concepto": "A"},
    {"id": "plan_2", "template_id": T2, "concepto": "B"},
]
COPIES = [
    {
        "plan_id": "plan_1", "template_id": T1,
        "headline": ["Hplan_1"], "primary_text": ["P"], "description": ["D"],
        "cta": ["LEARN_MORE", "NOPE"],  # "NOPE" is not in the CTA catalog -> dropped
        "template_elements": [
            {"element_id": "01_title", "element_type": "text", "text": "Txt plan_1", "purpose": "title"},
        ],
    },
    {
        "plan_id": "plan_2", "template_id": T2,
        "headline": ["Hplan_2"], "primary_text": ["P"], "description": ["D"],
        "cta": ["LEARN_MORE", "NOPE"],
        "template_elements": [
            {"element_id": "text_0", "element_type": "text", "text": "Txt plan_2", "purpose": "title"},
        ],
    },
]
IMAGE_PROMPTS = [
    {"plan_id": "plan_1", "template_id": T1, "image_prompts": [{"element_id": "img", "image_prompt": "x plan_1"}]},
    {"plan_id": "plan_2", "template_id": T2, "image_prompts": [{"element_id": "img", "image_prompt": "x plan_2"}]},
]
VALIDATION = {"overall_pass": True, "subset_to_regenerate": []}


def _fake_run_agent() -> FakeRunAgent:
    return FakeRunAgent({
        ESTRATEGA: [PLANS],
        COPYWRITER: [COPIES],
        IMAGE_PROMPTER: [IMAGE_PROMPTS],
        VALIDADOR: [VALIDATION],
    })


# ---------------------------------------------------------------------------
# Golden reference (recorded from the pre-change code; literal on purpose)
# `<ADSET_CONTEXT_JSON>` stands for json.dumps(mock Adset_Context, ensure_ascii=False).
# ---------------------------------------------------------------------------

CTX_PLACEHOLDER = "<ADSET_CONTEXT_JSON>"

GOLDEN_USER_IDS = [
    "adset_173_ad_901_strat",
    "adset_173_ad_901_copy",
    "adset_173_ad_901_img",
    "adset_173_ad_901_val_1",
]

GOLDEN_SEQUENCE: list[tuple[str, str]] = [
    (
        "estratega_agent",
        "n_variants=2. id_adset=173 ad_id=901 project_id=test-project-id\n"
        "Design 2 ad strategy plans.\n"
        "FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n"
        "<ADSET_CONTEXT_JSON>\n",
    ),
    (
        "copywriter_agent",
        "Generate copy for these 2 plans.\n"
        'Plans: [{"id": "plan_1", "template_id": "f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4", "concepto": "A"}, '
        '{"id": "plan_2", "template_id": "612e957c-44f7-4d6c-be98-5ecd8392673d", "concepto": "B"}]\n'
        "id_adset=173 ad_id=901 project_id=test-project-id\n"
        "FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n"
        "<ADSET_CONTEXT_JSON>\n",
    ),
    (
        "image_prompter_agent",
        "Generate image prompts for these plans.\n"
        'Plans: [{"id": "plan_1", "template_id": "f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4", "concepto": "A"}, '
        '{"id": "plan_2", "template_id": "612e957c-44f7-4d6c-be98-5ecd8392673d", "concepto": "B"}]\n'
        'Copies: [{"plan_id": "plan_1", "template_id": "f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4", '
        '"headline": ["Hplan_1"], "primary_text": ["P"], "description": ["D"], "cta": ["LEARN_MORE"], '
        '"template_elements": [{"element_id": "01_title", "element_type": "text", "text": "Txt plan_1", "purpose": "title"}]}, '
        '{"plan_id": "plan_2", "template_id": "612e957c-44f7-4d6c-be98-5ecd8392673d", '
        '"headline": ["Hplan_2"], "primary_text": ["P"], "description": ["D"], "cta": ["LEARN_MORE"], '
        '"template_elements": [{"element_id": "text_0", "element_type": "text", "text": "Txt plan_2", "purpose": "title"}]}]\n'
        "id_adset=173 ad_id=901\n"
        "FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n"
        "<ADSET_CONTEXT_JSON>\n",
    ),
    (
        "validador_agent",
        "Validate these 2 proposals:\n"
        '[{"ad_id": 901, "plan_id": "plan_1", '
        '"plan": {"id": "plan_1", "template_id": "f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4", "concepto": "A"}, '
        '"copy": {"plan_id": "plan_1", "template_id": "f25fc5e4-0382-4fc0-b94b-86bbe7a3f9a4", '
        '"headline": ["Hplan_1"], "primary_text": ["P"], "description": ["D"], "cta": ["LEARN_MORE"], '
        '"template_elements": [{"element_id": "01_title", "element_type": "text", "text": "Txt plan_1", "purpose": "title"}]}, '
        '"image_prompts": [{"element_id": "img", "image_prompt": "x plan_1"}]}, '
        '{"ad_id": 901, "plan_id": "plan_2", '
        '"plan": {"id": "plan_2", "template_id": "612e957c-44f7-4d6c-be98-5ecd8392673d", "concepto": "B"}, '
        '"copy": {"plan_id": "plan_2", "template_id": "612e957c-44f7-4d6c-be98-5ecd8392673d", '
        '"headline": ["Hplan_2"], "primary_text": ["P"], "description": ["D"], "cta": ["LEARN_MORE"], '
        '"template_elements": [{"element_id": "text_0", "element_type": "text", "text": "Txt plan_2", "purpose": "title"}]}, '
        '"image_prompts": [{"element_id": "img", "image_prompt": "x plan_2"}]}]',
    ),
]

LEGACY_RESULT_KEYS = {
    "variant_job_id", "id_adset", "status", "abyssale_batch_ids",
    "proposals", "validation_reports", "saved_ads",
}


def _expected_sequence(ctx: Any) -> list[tuple[str, str]]:
    ctx_json = json.dumps(ctx, ensure_ascii=False)
    return [(name, msg.replace(CTX_PLACEHOLDER, ctx_json)) for name, msg in GOLDEN_SEQUENCE]


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

_FLAG = "USE_ADSET_CREATIVE_DIVERSITY"
_MISSING = object()

# P15 Image_Elements helpers the Legacy_Path must never call (Req 15.15, 12.36).
_ADSET_DIVERSITY = "services.adset_diversity"
FORBIDDEN_IMAGE_ELEMENT_HELPERS = (
    "check_image_elements",
    "template_image_elements",
    "filter_image_prompts",
)


class _ForbiddenHelper:
    """Stand-in for a P15 helper: records the call and fails the test.

    The call is recorded before raising so a broad `except` in the pipeline
    cannot hide it (the harness asserts the record is empty after the run)."""

    def __init__(self, name: str, record: list[str]) -> None:
        self.name = name
        self.record = record

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.record.append(self.name)
        pytest.fail(f"Legacy_Path called services.adset_diversity.{self.name} (P15, Req 15.15)")


class _CallerTrackingTemplateDefinition(FakeGetATemplateDefinition):
    """FakeGetATemplateDefinition that also records the awaiting function's name."""

    def __init__(self) -> None:
        super().__init__()
        self.callers: list[str] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # Inside a running coroutine, frame 1 is the coroutine that awaited it.
        self.callers.append(sys._getframe(1).f_code.co_name)
        return await super().__call__(*args, **kwargs)


@contextmanager
def _legacy_run(flag_mode: str) -> Iterator[tuple[Any, dict, Any]]:
    """Run `_run_phase1` on the Legacy_Path with the flag False or absent.

    The P15 Image_Elements helpers are replaced by `_ForbiddenHelper`s and
    `get_a_template_definition` by a caller-tracking fake, exposed on the harness
    as `h.forbidden_calls` and `h.get_a_template_definition`."""
    ctx = make_adset_context()
    run_agent = _fake_run_agent()
    forbidden_calls: list[str] = []
    with patched_diversity_pipeline(
        adset_context=ctx,
        run_agent=run_agent,
        get_a_template_definition=_CallerTrackingTemplateDefinition(),
        diversity_flag=False if flag_mode == "false" else None,
        extra_patches=[
            (_ADSET_DIVERSITY, name, _ForbiddenHelper(name, forbidden_calls))
            for name in FORBIDDEN_IMAGE_ELEMENT_HELPERS
        ],
    ) as h:
        h.forbidden_calls = forbidden_calls
        saved = _MISSING
        if flag_mode == "absent":
            saved = h.settings.__dict__.pop(_FLAG, _MISSING)
        try:
            result = run_phase1(id_adset=ID_ADSET, id_ad=ID_AD, n_variants=N_VARIANTS)
        finally:
            if saved is not _MISSING:
                object.__setattr__(h.settings, _FLAG, saved)
        assert forbidden_calls == [], f"Legacy_Path called P15 helpers: {forbidden_calls}"
        yield h, result, ctx


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag_mode", ["false", "absent"])
def test_legacy_agent_sequence_matches_golden(flag_mode: str) -> None:
    with _legacy_run(flag_mode) as (h, _result, ctx):
        assert h.run_agent.sequence == _expected_sequence(ctx)
        assert [c.user_id for c in h.run_agent.calls] == GOLDEN_USER_IDS


@pytest.mark.parametrize("flag_mode", ["false", "absent"])
def test_legacy_result_keys_and_no_territory_checkpoint(flag_mode: str) -> None:
    with _legacy_run(flag_mode) as (h, result, _ctx):
        assert set(result) == LEGACY_RESULT_KEYS
        assert "diversity_reports" not in result
        assert result["variant_job_id"] == DEFAULT_TASK_ID
        assert result["id_adset"] == ID_ADSET
        assert result["status"] == "WAITING_ABYSSALE"
        assert result["validation_reports"] == [VALIDATION]
        assert [s["plan_id"] for s in result["saved_ads"]] == ["plan_1", "plan_2"]
        assert all(s["saved"] for s in result["saved_ads"])
        assert len(result["abyssale_batch_ids"]) == 1

        # No adset_territories Checkpoint written, under any ad/adset key.
        assert not [k for k in h.redis.written_keys if k.endswith(":adset_territories")]
        assert h.redis.checkpoint(DEFAULT_TASK_ID, ID_ADSET, "adset_territories") is None
        if h.assign_territories is not None:
            assert h.assign_territories.call_count == 0


@pytest.mark.parametrize("flag_mode", ["false", "absent"])
def test_legacy_p15_no_image_elements_and_one_template_definition_per_copy(flag_mode: str) -> None:
    """P15 leaves the Legacy_Path as is (Req 15.15, 12.13, 12.36): no Image_Elements
    helper is called and `get_a_template_definition` runs once per copy, in copy
    order, only from `_build_save_ads_payloads` (no job cache, no `resolve_template`)."""
    with _legacy_run(flag_mode) as (h, _result, _ctx):
        assert h.forbidden_calls == []
        fake = h.get_a_template_definition
        assert fake.call_count == len(COPIES)
        assert [c.arguments.get("template_id") for c in fake.calls] == [c["template_id"] for c in COPIES]
        assert fake.callers == ["_build_save_ads_payloads"] * len(COPIES)


if __name__ == "__main__":
    for mode in ("false", "absent"):
        test_legacy_agent_sequence_matches_golden(mode)
        print(f"  PASS  test_legacy_agent_sequence_matches_golden[{mode}]")
        test_legacy_result_keys_and_no_territory_checkpoint(mode)
        print(f"  PASS  test_legacy_result_keys_and_no_territory_checkpoint[{mode}]")
        test_legacy_p15_no_image_elements_and_one_template_definition_per_copy(mode)
        print(f"  PASS  test_legacy_p15_no_image_elements_and_one_template_definition_per_copy[{mode}]")
    print("\nLEGACY GOLDEN PASS")
