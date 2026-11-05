# Ads Assembly v2 — Phase-A Territory Engine: rollout & validation

The deterministic creative-territory engine (Phase A) is built, unit-tested, and wired
into `_run_phase1` behind a flag. It is **off by default**. This is how to turn it on and
validate it in a real (LLM-reachable) environment — dev or QAS.

> Why not validated locally: the dev host is geo-blocked from the Gemini API
> ("User location is not supported") and has no funded fallback key, so the LLM step
> can't run here. All deterministic logic is verified locally (10/10 tests); only the
> live concept-writing needs a reachable environment.

## What's on the branch `fix/adsassembly-context-fetch-once`
- `services/territory_assignment.py` — assign disjoint territories (code) + LLM bridge.
- `agents/estratega_adset_agent.py` — the Phase-A agent (writes concepts within territories).
- `schemas/territory_schemas.py` — `AdsetHypothesis` (N2) + `AdDescription` (N3).
- `services/ads_validators.py::validate_estratega_adset_response` — parses the LLM output.
- `services/job_runner_service.py` — flag-gated Phase-A branch in STEP 2 (Strategy).
- `core/config.py::USE_TERRITORY_ENGINE` — the flag (default `False`).
- `tests/test_territory_assignment.py` — 10 invariant tests.

## Step 1 — create the Langfuse prompt `fury.estratega_adset`
On **langfuse-qas** (and langfuse-dev), create a prompt named exactly `fury.estratega_adset`:
- **Content:** paste the seed instruction verbatim from
  `agents/estratega_adset_agent.py` → `_FALLBACK_INSTRUCTION` (the whole triple-quoted block).
- **Config (JSON):** `{ "model": "gemini/gemini-2.5-pro" }`
  ⚠️ Keep the **`gemini/` prefix** — bare `gemini-2.5-pro` routes to Vertex and throws
  `DefaultCredentialsError` (this was the QAS `ERR_PROCESSING_LLM` cause).
- **Label:** `latest` (the app loads prompts by `label="latest"`).

If the prompt is absent the agent falls back to the same seed text + `gemini/gemini-2.5-pro`,
so it still works — creating it just makes the prompt tunable without a deploy.

## Step 2 — enable the flag in the target env
Set in the environment (env var or config):
```
USE_TERRITORY_ENGINE=true
```
Leave everything else as-is. Off = the legacy `estratega` path runs, byte-for-byte unchanged.

## Step 3 — trigger a variant job
Run the normal variant-generation flow for a real ad set (same call the app makes today —
e.g. the `/variants` endpoint / `run_pipeline_phase1`). Use a small `n_variants` (3–6) first.

## Step 4 — confirm it took the territory path
In the worker logs you should see (per ad):
- `→ phase_a_territories ad=… n=…`
- `territory engine -> N plans for ad=…`
(If you instead see `→ strategy …` with no `phase_a_*`, the flag isn't set or the engine
found no anchors and fell back to legacy — check the adset has product/buyer data.)

## Step 5 — verify the output is distinct-by-construction
For the N generated ads in the set, confirm:
- **Distinct primary anchors** — no two ads lead on the same product/buyer point.
- **Disjoint style axes** — emocion / visual_dominante / etc. differ across ads.
- **Umbrella coherence** — all concepts recognizably share the campaign's Big Idea.
- **Distinct templates** — each ad maps to a different Abyssale template (when templates exist).
- Spot-check against a legacy run (flag off) on the same adset — the territory set should be
  visibly more differentiated and should NOT collapse toward one dominant creative.

## Rollback
Set `USE_TERRITORY_ENGINE=false`. Instant revert to the legacy path; no data migration.

## Known follow-ups (not blockers for this validation)
- Real Sinergia `/adset/{id}` must expose the umbrella vars (mock already does; see
  `campaign_tools.get_adset_context` NOTE). Until then, umbrella coherence is only exercised
  by the mock.
- Phase B (Ad→Variants whitelist operators) + the semantic two-threshold gate are the next
  build steps; this rollout covers Phase A (territory assignment + concept writing) only.
