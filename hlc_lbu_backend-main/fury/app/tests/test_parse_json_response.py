"""Regression tests for _parse_json_response idempotency (persona + ads job runners).

Guards the fix for Carlos's persona failures:

    'dict' object has no attribute 'strip'   (step: persona_data_collector_agent)

`run_agent` is documented as returning text, but returns `ValidationResult.data`
— already-parsed JSON — whenever a validator supplies it, which every persona
validator does. Call sites then passed that dict to `_parse_json_response`,
which did `text.strip()` and blew up.

The ads pipeline had every call site commented out; the persona pipeline only
had two of six, so the EDIT and VARIANTS flows crashed. Rather than chase the
remaining call sites by hand (which is how two got missed), the parse itself is
now idempotent — an already-parsed dict/list passes straight through.

Runnable two ways:
    python -m tests.test_parse_json_response      # plain asserts, prints a summary
    pytest tests/test_parse_json_response.py      # standard collection
"""
from __future__ import annotations

from services.persona_job_runner_service import _parse_json_response as persona_parse
from services.job_runner_service import _parse_json_response as ads_parse

_PARSERS = (("persona", persona_parse), ("ads", ads_parse))


def test_already_parsed_dict_passes_through():
    # THE regression: run_agent returned the validator's parsed data (a dict).
    ctx = {"persona": {"name": "Anna"}, "product": None}
    for name, parse in _PARSERS:
        assert parse(ctx) == ctx, name
        assert parse(ctx) is ctx, f"{name}: should return the same object, not a copy"


def test_already_parsed_list_passes_through():
    # Some validators (e.g. estratega_adset) parse to a LIST, not a dict.
    plans = [{"id": "plan_1"}, {"id": "plan_2"}]
    for name, parse in _PARSERS:
        assert parse(plans) == plans, name


def test_empty_dict_is_not_mistaken_for_empty_response():
    # {} is falsy — it must still round-trip as {}, not be treated as "empty text".
    for name, parse in _PARSERS:
        assert parse({}) == {}, name
        assert parse([]) == [], name


def test_plain_json_string_still_parses():
    for name, parse in _PARSERS:
        assert parse('{"a": 1}') == {"a": 1}, name
        assert parse('[{"id": "x"}]') == [{"id": "x"}], name


def test_markdown_fenced_json_still_parses():
    fenced = '```json\n{"overall_pass": true}\n```'
    for name, parse in _PARSERS:
        assert parse(fenced) == {"overall_pass": True}, name


def test_empty_and_none_text_return_empty_dict():
    for name, parse in _PARSERS:
        assert parse("") == {}, name
        assert parse("   ") == {}, name
        assert parse(None) == {}, name


def test_the_exact_crash_no_longer_raises():
    # Reproduces the reported failure verbatim: a dict reaching the parser.
    for name, parse in _PARSERS:
        try:
            parse({"id_buyer_persona": 146})
        except AttributeError as e:  # pragma: no cover
            raise AssertionError(f"{name}: regression is back — {e}")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all parse-json-response tests passed")
