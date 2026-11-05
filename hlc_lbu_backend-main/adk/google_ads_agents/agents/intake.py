"""Intake pipeline: voice interview + brief compilation."""

from google.adk.agents import Agent, SequentialAgent

from ..config import MODEL_FLASH, MODEL_STD
from ..prompts.intake_prompt import VOICE_INTAKE_INSTRUCTION, BRIEF_COMPILER_INSTRUCTION
from ..schemas.campaign_brief import CampaignBrief


voice_intake_agent = Agent(
    name="voice_intake_agent",
    model=MODEL_FLASH,
    description="Interviews the client with 15 strategic questions about their business and Google Ads goals.",
    instruction=VOICE_INTAKE_INSTRUCTION,
    output_key="app:intake_raw_transcript",
)

brief_compiler_agent = Agent(
    name="brief_compiler_agent",
    model=MODEL_STD,
    description="Compiles the raw interview transcript into a structured CampaignBrief.",
    instruction=BRIEF_COMPILER_INSTRUCTION,
    output_key="app:campaign_brief",
    output_schema=CampaignBrief,
)

intake_pipeline = SequentialAgent(
    name="intake_pipeline",
    description="Client intake flow: interviews the client then compiles a structured campaign brief.",
    sub_agents=[voice_intake_agent, brief_compiler_agent],
)
