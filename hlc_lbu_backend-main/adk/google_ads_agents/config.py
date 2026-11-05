"""Shared configuration for the Google Ads multi-agent system.

Authentication:
    Gemini is accessed via Vertex AI using the Cloud Run service account's
    Application Default Credentials (ADC). No API key is needed.
    The SA (hiluca-adk-dev-sa) has roles/aiplatform.user.

    GOOGLE_GENAI_USE_VERTEXAI=TRUE  → ADK uses Vertex AI (set in Cloud Run env)
    GOOGLE_CLOUD_PROJECT            → GCP project (set in Cloud Run env)
    GOOGLE_CLOUD_LOCATION           → us-central1 (set in Cloud Run env)

Available models (verified in project careful-acumen-422922-k4 / us-central1):
    gemini-2.5-flash  → returns 400 INVALID_ARGUMENT (valid - just needs role field, ADK handles this)
    gemini-2.5-pro    → returns 400 INVALID_ARGUMENT (valid - same)
    gemini-2.0-flash  → returns 404 (not available in this project)
    gemini-1.5-*      → returns 404 (not available in this project)
"""

# ── Model tiers (Vertex AI, verified available in this project) ───────────────

MODEL_PRO   = "gemini-2.5-pro"    # strategy_agent, ad_copy_agent, diagnosis_agent
MODEL_FLASH = "gemini-2.5-flash"  # voice_intake, keyword_research, competitor_research,
                                   # trend_detection, implementation, monitor, action, reporting
MODEL_STD   = "gemini-2.5-flash"  # brief_compiler_agent, checkpoint_agent
MODEL_EXP   = "gemini-2.5-pro"   # experiment_agent

# Legacy alias
MODEL = MODEL_FLASH
