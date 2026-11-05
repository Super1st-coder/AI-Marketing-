"""Safety Guards — before_model_callback and after_model_callback for all Fury agents.

Applied to every Agent in the pipeline to block harmful content flowing INTO
the LLM (input guard) or coming OUT of the LLM (output guard).

Blocked categories
------------------
- credentials      — passwords, API keys, secrets
- csam             — child sexual abuse material
- hacking          — exploit payloads, malware, injection attacks
- hate_speech      — violent or dehumanising language
"""
import re
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types as genai_types

from core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Blocked keyword lists (case-insensitive; extend freely)
# ---------------------------------------------------------------------------

_BLOCKED: dict[str, list[str]] = {
    "credentials": [
        r"\bpassword\b",
        r"\bcontraseña\b",
        r"\bapi[_\s]?key\b",
        r"\bsecret[_\s]?key\b",
        r"\baccess[_\s]?token\b",
        r"\bprivate[_\s]?key\b",
        r"\bcredential",
        r"\bauth[_\s]?token\b",
        r"\bbearer\s+\S{10,}\b",  # Bearer <token>
    ],
    "csam": [
        r"\bpedofili",
        r"\bpedophil",
        r"\bchild\s+(sex|porn|nude|naked|abuse)",
        r"\bmenor(es)?\s+(sexual|desnud|abuso|porn)",
        r"\bcp\s+(content|porn|image)",
        r"\bunderage\s+(sex|nude|porn)",
        r"\blolita\s+(sex|nude|porn)",
    ],
    "hacking": [
        r"\bsql\s?injection\b",
        r"\bshell\s?injection\b",
        r"\bxss\s?payload\b",
        r"\bremote\s?code\s?execution\b",
        r"\bransomware\b",
        r"\bmalware\b",
        r"\bexploit\s+(code|payload|script)\b",
        r"\brootkit\b",
        r"\bkeylogger\b",
        r"\bphishing\s+(site|page|kit)\b",
        r"\bbotnet\b",
        r"\bddos\s+attack\b",
        r"(hack|crackear|hackear)\s+(password|cuenta|sistema|server)",
    ],
    "hate_speech": [
        r"\bgenocid[eo]\b",
        r"\bkill\s+all\s+\w+",
        r"\bethnic\s+cleansing\b",
        r"\bwhite\s+supremac",
        r"\bnazi\b",
        r"\bterrorist\s+(attack|bomb|plan)\b",
    ],
}

_COMPILED: dict[str, list[re.Pattern]] = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in _BLOCKED.items()
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _blocked_response(category: str, direction: str) -> LlmResponse:
    """Build a safe, structured LlmResponse that replaces the real call/response."""
    message = (
        f"[SAFETY_GUARD] {direction.upper()} content blocked. "
        f"Category: {category}. This request cannot be processed."
    )
    return LlmResponse(
        content=genai_types.Content(
            role="model",
            parts=[genai_types.Part(text=message)],
        )
    )


def _scan_text(text: str) -> Optional[str]:
    """Scan a text string against all blocked patterns.

    Returns:
        Category name (str) if a match is found, None if the text is clean.
    """
    for category, patterns in _COMPILED.items():
        for pattern in patterns:
            if pattern.search(text):
                return category
    return None


def _extract_text_from_request(llm_request: LlmRequest) -> str:
    """Pull all text content out of an LlmRequest for scanning."""
    parts: list[str] = []

    if llm_request.config and llm_request.config.system_instruction:
        si = llm_request.config.system_instruction
        if isinstance(si, genai_types.Content):
            for part in si.parts or []:
                if part.text:
                    parts.append(part.text)
        elif isinstance(si, str):
            parts.append(si)

    for content in llm_request.contents or []:
        for part in content.parts or []:
            if part.text:
                parts.append(part.text)

    return "\n".join(parts)


def _extract_text_from_response(llm_response: LlmResponse) -> str:
    """Pull all text content out of an LlmResponse for scanning."""
    parts: list[str] = []
    if llm_response.content:
        for part in llm_response.content.parts or []:
            if part.text:
                parts.append(part.text)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# ADK Callbacks — applied to ALL agents
# ---------------------------------------------------------------------------

def safety_guard_before_model(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """INPUT guard — scans request content before it reaches the LLM.

    If harmful content is detected:
    - Logs the event (Loguru)
    - Marks the session state so the orchestrator can log to Langfuse
    - Returns a safe LlmResponse immediately (LLM call is SKIPPED)

    If clean:
    - Returns None (normal execution continues)
    """
    agent_name = getattr(callback_context, "agent_name", "unknown")
    text = _extract_text_from_request(llm_request)

    category = _scan_text(text)
    if category:
        logger.warning(
            f"[safety_guard] INPUT blocked | agent={agent_name} | category={category}"
        )
        callback_context.state["safety_blocked"] = True
        callback_context.state["safety_category"] = category
        callback_context.state["safety_direction"] = "input"

        return _blocked_response(category, "input")

    return None  # clean — let the LLM call proceed


def safety_guard_after_model(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """OUTPUT guard — scans LLM response before it's delivered to the agent.

    If harmful content is detected in the response:
    - Logs the event
    - Replaces the response with a safe blocked message

    If clean:
    - Returns None (original response is delivered as-is)
    """
    agent_name = getattr(callback_context, "agent_name", "unknown")
    text = _extract_text_from_response(llm_response)

    category = _scan_text(text)
    if category:
        logger.warning(
            f"[safety_guard] OUTPUT blocked | agent={agent_name} | category={category}"
        )
        callback_context.state["safety_blocked"] = True
        callback_context.state["safety_category"] = category
        callback_context.state["safety_direction"] = "output"

        return _blocked_response(category, "output")

    return None
