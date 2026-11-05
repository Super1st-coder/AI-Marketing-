"""Optimization loop: monitor + diagnose + act + checkpoint (loop agent)."""

from google.adk.agents import Agent, LoopAgent

from ..config import MODEL_PRO, MODEL_FLASH, MODEL_STD
from ..prompts.optimization_prompt import (
    MONITOR_INSTRUCTION, DIAGNOSIS_INSTRUCTION,
    ACTION_INSTRUCTION, CHECKPOINT_INSTRUCTION,
)
from ..tools.google_ads_reporting import (
    get_campaign_performance, get_keyword_performance,
    get_search_term_report, get_ad_performance,
)
from ..tools.google_ads_optimization import (
    get_recommendations, apply_recommendation,
    update_keyword_bid, update_campaign_budget,
    pause_keyword, update_bidding_strategy,
)
from ..tools.google_ads_campaigns import add_negative_keywords


monitor_agent = Agent(
    name="monitor_agent",
    model=MODEL_FLASH,
    description="Pulls fresh campaign performance data and compares to targets.",
    instruction=MONITOR_INSTRUCTION,
    tools=[get_campaign_performance, get_keyword_performance, get_search_term_report, get_ad_performance],
    output_key="app:performance_snapshot",
)

diagnosis_agent = Agent(
    name="diagnosis_agent",
    model=MODEL_PRO,
    description="Analyzes performance data to identify problems and opportunities.",
    instruction=DIAGNOSIS_INSTRUCTION,
    output_key="app:diagnosis_result",
)

action_agent = Agent(
    name="action_agent",
    model=MODEL_FLASH,
    description="Executes optimization changes: bid adjustments, keyword pauses, budget reallocation.",
    instruction=ACTION_INSTRUCTION,
    tools=[
        get_recommendations, apply_recommendation,
        update_keyword_bid, update_campaign_budget,
        pause_keyword, update_bidding_strategy,
        add_negative_keywords,
    ],
    output_key="app:optimization_log",
)

checkpoint_agent = Agent(
    name="checkpoint_agent",
    model=MODEL_STD,
    description="Decides whether to continue optimizing or exit the loop.",
    instruction=CHECKPOINT_INSTRUCTION,
    output_key="app:optimization_checkpoint",
)

optimization_loop = LoopAgent(
    name="optimization_loop",
    description="Continuously monitors, diagnoses, optimizes, and validates campaign performance.",
    max_iterations=5,
    sub_agents=[monitor_agent, diagnosis_agent, action_agent, checkpoint_agent],
)
