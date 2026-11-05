"""Experiment agent: proposes and manages A/B tests."""

from google.adk.agents import Agent

from ..config import MODEL_EXP
from ..prompts.reporting_prompt import EXPERIMENT_INSTRUCTION
from ..tools.google_ads_reporting import get_campaign_performance, get_keyword_performance
from ..tools.competitor_tools import analyze_competitor_ads
from ..tools.trend_tools import get_google_trends, get_industry_news
from ..tools.experiment_tools import create_campaign_draft, create_experiment, get_experiment_results


experiment_agent = Agent(
    name="experiment_agent",
    model=MODEL_EXP,
    description="Proposes and manages A/B test experiments to improve campaign performance.",
    instruction=EXPERIMENT_INSTRUCTION,
    tools=[
        get_campaign_performance, get_keyword_performance,
        analyze_competitor_ads, get_google_trends, get_industry_news,
        create_campaign_draft, create_experiment, get_experiment_results,
    ],
)
