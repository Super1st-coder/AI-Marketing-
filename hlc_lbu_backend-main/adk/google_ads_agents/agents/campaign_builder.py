"""Campaign builder pipeline: strategy + ad copy + implementation (sequential)."""

from google.adk.agents import Agent, SequentialAgent

from ..config import MODEL_PRO, MODEL_FLASH
from ..prompts.strategy_prompt import STRATEGY_INSTRUCTION, AD_COPY_INSTRUCTION, IMPLEMENTATION_INSTRUCTION
from ..schemas.campaign_structure import CampaignStructure
from ..tools.google_ads_campaigns import (
    create_campaign, create_ad_group, add_keywords,
    create_responsive_search_ad, add_negative_keywords,
)
from ..tools.google_ads_assets import validate_ad_copy


strategy_agent = Agent(
    name="strategy_agent",
    model=MODEL_PRO,
    description="Designs the optimal campaign structure based on research and brief.",
    instruction=STRATEGY_INSTRUCTION,
    output_key="app:campaign_structure",
    output_schema=CampaignStructure,
)

ad_copy_agent = Agent(
    name="ad_copy_agent",
    model=MODEL_PRO,
    description="Generates responsive search ad copy for each ad group.",
    instruction=AD_COPY_INSTRUCTION,
    tools=[validate_ad_copy],
    output_key="app:ad_copy_variants",
)

implementation_agent = Agent(
    name="implementation_agent",
    model=MODEL_FLASH,
    description="Creates campaigns, ad groups, keywords, and ads in Google Ads via API.",
    instruction=IMPLEMENTATION_INSTRUCTION,
    tools=[create_campaign, create_ad_group, add_keywords, create_responsive_search_ad, add_negative_keywords],
    output_key="app:campaign_ids",
)

campaign_builder_pipeline = SequentialAgent(
    name="campaign_builder_pipeline",
    description="Builds campaigns: designs strategy, writes ad copy, then implements in Google Ads.",
    sub_agents=[strategy_agent, ad_copy_agent, implementation_agent],
)
