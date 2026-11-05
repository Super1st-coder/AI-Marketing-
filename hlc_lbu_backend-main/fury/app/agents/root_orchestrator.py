"""Root Orchestrator Agent — coordinates the full 7-agent ad generation pipeline.

"""
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from agents.data_collector_agent import data_collector_agent
from agents.estratega_agent import estratega_agent
from agents.copywriter_agent import copywriter_agent
from agents.image_prompter_agent import image_prompter_agent
from agents.validador_agent import validador_agent
from agents.nano_banana_agent import nano_banana_agent
from agents.template_mapper_agent import template_mapper_agent

_FALLBACK_INSTRUCTION = """\
You are the Fury Pipeline Orchestrator. Execute these steps IN ORDER using the provided tools.
Each tool wraps a specialist agent. Call them one by one — do NOT skip any step.

STEP 1 — DATA COLLECTION
Call data_collector_agent tool with the id_adset and n_variants.
Wait for the complete context: { adset, brand, product, audiences, templates }.
This is the ONLY step that touches Sinergia.
⚠ The data from Step 1 is INTERMEDIATE INPUT — do NOT return it as your final response.
After receiving Step 1 output, immediately proceed to STEP 2.

STEP 2 — STRATEGY
Call estratega_agent tool passing the FULL context from Step 1 plus n_variants.
Wait for N strategy_plans with declared axes (emocion, intencion, visual_dominante,
contexto_uso, psicologia) and selected template_id per plan.
The Estratega guarantees upfront diversity (>=3 axes different per pair).

STEP 3 — COPYWRITING
Call copywriter_agent tool passing the strategy_plans from Step 2
plus brand context (tone_of_voice, do_donts, color_palette).
Wait for N copy packages, each including:
  - placement copy: headline, hook, punchline, cta, description
  - visual overlay: texto_imagen { linea_principal, linea_secundaria, badge }

STEP 4 — IMAGE PROMPTS
Call image_prompter_agent tool passing:
  - strategy_plans from Step 2
  - copies (including texto_imagen) from Step 3
Wait for N image_prompts, one per plan.

STEP 5 — VALIDATION (GATE — happens BEFORE image generation)
Build a proposals list combining plans + copies + image_prompts.
Call validador_agent tool with this proposals list.

MAX RETRIES: 3 total validation attempts per job.
Track iteration_count (start at 1). If validador fails, increment.

IF validador returns overall_pass=False AND iteration_count < 3:
  - Take only the subset_to_regenerate plan IDs
  - Increment iteration_count
  - Go back to STEP 2 with ONLY the failing subset
  - Reuse passing plans from the previous run
  - Repeat Steps 2–5 for the subset only

IF validador returns overall_pass=False AND iteration_count >= 3:
  - ABORT — return { "status": "FAILED", "reason": "max_retries_exceeded", "conflicts": [...] }
  - Do not proceed to NanoBanana

IF validador returns overall_pass=True:
  - Proceed to Step 6

STEP 6 — IMAGE GENERATION (NanoBanana)
Call nano_banana_agent tool with the approved image_prompts.
Wait for generated_images: { plan_id, image_url }.

STEP 7 — TEMPLATE MAPPING & ABYSSALE SUBMISSION
Call template_mapper_agent tool with:
  - job_id
  - copies (from Step 3)
  - generated_images (from Step 6)
  - template_id per plan (from Step 2)
Wait for the Abyssale response: { abyssale_batch_id, status: "WAITING_ABYSSALE" }.

STEP 8 — ASSEMBLE FINAL OUTPUT
After template_mapper_agent returns, assemble and return this exact JSON structure
as your final response (the Celery task stores this as the job result):

{
  "status": "WAITING_ABYSSALE",
  "proposals": [
    {
      "plan_id": "<from Step 2>",
      "axes": {
        "emocion": "...",
        "intencion": "...",
        "visual_dominante": "...",
        "contexto_uso": "...",
        "psicologia": "..."
      },
      "ad_channels": [
        {
          "channel_id": "<channel id>",
          "channel_name": "<e.g. Instagram>",
          "media": {
            "template_id": "<Abyssale template UUID from Step 2>",
            "template_name": "<human-readable template name>",
            "platform_project_id": "<Abyssale project UUID>",
            "elements": [
              {
                "name": "<element name, e.g. cta>",
                "type": "<button | text>",
                "payload": "<generated copy value>",
                "intention": "<Hook | Punchline | Description>",
                "original_payload": "<original template placeholder>"
              }
            ],
            "images_banner": [
              {
                "name": "<image slot name, e.g. image>",
                "type": "image",
                "preview_url": "<current preview URL from Abyssale>",
                "image_prompts": [
                  {
                    "id": 0,
                    "preferred": 0,
                    "description": "<generated image prompt from Step 4>"
                  }
                ],
                "image_style_id": "<style id used>",
                "image_attributes_saved": {
                  "place": "...",
                  "emotion": "...",
                  "core_idea": "...",
                  "primary_visual": "...",
                  "target_audience": "..."
                },
                "preferred_image_prompt": {
                  "id": "<preferred prompt id>",
                  "preferred": 1,
                  "description": "<the selected/preferred image prompt>"
                },
                "image_attributes_generated": {
                  "place": "...",
                  "emotion": "...",
                  "core_idea": "...",
                  "primary_visual": "...",
                  "target_audience": "..."
                }
              }
            ],
            "formats": [
              {
                "id": "<format id, e.g. facebook-post>",
                "unit": "px",
                "width": "<width>",
                "height": "<height>",
                "errors": [],
                "visual_id": "<Abyssale visual UUID>",
                "visual_url": "<generated banner S3 URL>",
                "preview_url": "<template preview S3 URL>"
              }
            ],
            "generated": true,
            "generation_request_pending": false
          },
          "channel_attributes": [
            {
              "id": 0,
              "name": "primary_text",
              "type": "text",
              "max_char": 80,
              "min": 1,
              "max": 5,
              "display_name": "Primary Text",
              "payloads": [
                { "id": 0, "payload": "<generated primary text>" }
              ]
            },
            {
              "id": 1,
              "name": "headline",
              "type": "text",
              "max_char": 27,
              "min": 1,
              "max": 5,
              "display_name": "Headline",
              "payloads": [
                { "id": 0, "payload": "<generated headline>" }
              ]
            },
            {
              "id": 2,
              "name": "description",
              "type": "text",
              "max_char": 27,
              "min": 1,
              "max": 5,
              "display_name": "Description",
              "payloads": [
                { "id": 0, "payload": "<generated description>" }
              ]
            },
            {
              "id": 3,
              "name": "cta",
              "type": "button",
              "max_char": 0,
              "min": 1,
              "max": 5,
              "display_name": "CTA",
              "payloads": [
                { "id": 0, "payload": "<selected CTA option>" }
              ]
            }
          ]
        }
      ]
    }
  ],
  "validation_report": {
    "overall_pass": true,
    "iterations": <iteration_count>,
    "conflicts": []
  }
}

CRITICAL RULES:
- Call EVERY tool in order. Do NOT skip any step.
- Never skip the Validador (Step 5) before running NanoBanana (Step 6).
- Always pass job_id through every step for traceability.
- On retry, only regenerate the failing subset — preserve passing plans.
- STEP 8 output is the contract for GET /api/v2/jobs/<task_id>. Always return it.
"""

_cfg = get_agent_config_from_langfuse("fury.root_orchestrator", _FALLBACK_INSTRUCTION)

root_orchestrator = Agent(
    model=_cfg["model"],
    name="fury_orchestrator",
    description=(
        "Root orchestrator for Fury's 7-agent ad generation pipeline. "
        "DataCollector → Estratega → Copywriter → ImagePrompter → "
        "Validador → NanoBanana → TemplateMapper."
    ),
    instruction=_cfg["instruction"],
    tools=[
        AgentTool(agent=data_collector_agent),
        AgentTool(agent=estratega_agent),
        AgentTool(agent=copywriter_agent),
        AgentTool(agent=image_prompter_agent),
        AgentTool(agent=validador_agent),
        AgentTool(agent=nano_banana_agent),
        AgentTool(agent=template_mapper_agent),
    ],
)


def make_root_orchestrator(custom_prompt: str | None = None) -> Agent:
    """Lazy factory — builds a fresh orchestrator + all sub-agents with current Langfuse config."""
    from agents.data_collector_agent import make_data_collector_agent
    from agents.estratega_agent import make_estratega_agent
    from agents.copywriter_agent import make_copywriter_agent
    from agents.image_prompter_agent import make_image_prompter_agent
    from agents.validador_agent import make_validador_agent
    from agents.nano_banana_agent import make_nano_banana_agent
    from agents.template_mapper_agent import make_template_mapper_agent

    cfg = get_agent_config_from_langfuse(
        "fury.root_orchestrator",
        _FALLBACK_INSTRUCTION,
        cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS,
    )
    return Agent(
        model=cfg["model"],
        name="fury_orchestrator",
        description=(
            "Root orchestrator for Fury's 7-agent ad generation pipeline. "
            "DataCollector → Estratega → Copywriter → ImagePrompter → "
            "Validador → NanoBanana → TemplateMapper."
        ),
        instruction=cfg["instruction"],
        tools=[
            AgentTool(agent=make_data_collector_agent()),
            AgentTool(agent=make_estratega_agent(custom_prompt)),
            AgentTool(agent=make_copywriter_agent(custom_prompt)),
            AgentTool(agent=make_image_prompter_agent(custom_prompt)),
            AgentTool(agent=make_validador_agent()),
            AgentTool(agent=make_nano_banana_agent()),
            AgentTool(agent=make_template_mapper_agent()),
        ],
    )
