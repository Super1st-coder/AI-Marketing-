"""Regression tests for the presigned-URL sanitizer (job_runner_service).

Guards the fix for the copywriter ERR_INVALID_JSON failure: Sinergia returns
brand logos as S3 *presigned* URLs whose query string contains
``X-Amz-Credential``. Injected raw into an agent prompt, that (a) leaks AWS
credentials to the LLM and (b) trips the credentials safety-guard, which skips
the LLM and returns "[SAFETY_GUARD] ... blocked" — failing JSON validation.

Runnable two ways:
    python -m tests.test_context_sanitizer      # plain asserts, prints a summary
    pytest tests/test_context_sanitizer.py      # standard collection
"""
from __future__ import annotations

from services.job_runner_service import _strip_signed_urls
from agents.guards.safety_guard import _scan_text

# A real-shaped presigned S3 URL (truncated, fake signature) — the exact shape
# that broke adset 295: the query carries X-Amz-Credential / -Security-Token.
_PRESIGNED = (
    "https://hiluca-assets-dev.s3.us-east-2.amazonaws.com/35/nike_logo.png"
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256"
    "&X-Amz-Credential=ASIA4RCAOHP6C6LWJLJB%2F20260513%2Fus-east-2%2Fs3%2Faws4_request"
    "&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEH4aFAKE"
    "&X-Amz-Signature=819861400f8c859613928fc2897e6bcda1b9d8"
    "&X-Amz-SignedHeaders=host"
)


def test_scan_text_catches_raw_presigned_url():
    # Sanity: the raw URL really does trip the credentials guard (the root cause).
    assert _scan_text(_PRESIGNED) == "credentials"


def test_strip_removes_signing_query_and_keeps_path():
    cleaned = _strip_signed_urls(_PRESIGNED)
    assert cleaned == "https://hiluca-assets-dev.s3.us-east-2.amazonaws.com/35/nike_logo.png"
    assert "X-Amz-Credential" not in cleaned


def test_sanitized_context_is_no_longer_blocked():
    # After stripping, the guard must see the context as clean.
    assert _scan_text(_strip_signed_urls(_PRESIGNED)) is None


def test_strip_is_recursive_over_nested_context():
    ctx = {
        "adset": {
            "brand": {
                "logos": {"values": [{"image_url": _PRESIGNED}, {"image_url": _PRESIGNED}]},
                "website": "https://www.nike.com/mx/",        # plain URL, no query
            },
            "product": {"name": "Total 90", "description": "Auténtico estilo de fútbol"},
        }
    }
    cleaned = _strip_signed_urls(ctx)
    logos = cleaned["adset"]["brand"]["logos"]["values"]
    assert all("X-Amz-" not in l["image_url"] for l in logos)
    # Untouched: plain URLs and free text survive verbatim.
    assert cleaned["adset"]["brand"]["website"] == "https://www.nike.com/mx/"
    assert cleaned["adset"]["product"]["description"] == "Auténtico estilo de fútbol"
    # And the whole cleaned blob is clean to the guard.
    import json
    assert _scan_text(json.dumps(cleaned, ensure_ascii=False)) is None


def test_strip_leaves_unsigned_query_urls_alone():
    # A normal query string (no signing markers) must not be stripped.
    url = "https://example.com/page?ref=nike&utm=ads"
    assert _strip_signed_urls(url) == url


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all context-sanitizer tests passed")
