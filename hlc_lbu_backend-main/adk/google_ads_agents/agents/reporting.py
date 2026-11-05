"""Reporting agent: on-demand performance reports."""

from google.adk.agents import Agent

from ..config import MODEL_FLASH
from ..prompts.reporting_prompt import REPORTING_INSTRUCTION
from ..tools.google_ads_reporting import (
    get_campaign_performance, get_keyword_performance,
    get_search_term_report, get_ad_performance,
)


reporting_agent = Agent(
    name="reporting_agent",
    model=MODEL_FLASH,
    description="Generates comprehensive Google Ads performance reports with insights and recommendations.",
    instruction=REPORTING_INSTRUCTION,
    tools=[get_campaign_performance, get_keyword_performance, get_search_term_report, get_ad_performance],
)
