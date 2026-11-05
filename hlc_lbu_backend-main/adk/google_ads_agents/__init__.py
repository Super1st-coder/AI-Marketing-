# Override ADK's global default model before anything else loads.
# Uses a stable Vertex AI GA model ID (GOOGLE_GENAI_USE_VERTEXAI=TRUE is set via Cloud Run env).
from google.adk.agents.llm_agent import LlmAgent
from .config import MODEL_FLASH

LlmAgent.set_default_model(MODEL_FLASH)

from . import agent
