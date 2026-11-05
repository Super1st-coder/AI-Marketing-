"""Research pipeline: keyword research → competitor analysis → trend detection (sequential).

Changed from ParallelAgent to SequentialAgent to prevent SSE stream crashes
caused by too many concurrent HTTP calls overwhelming the adk web connection.
"""

from google.adk.agents import Agent, SequentialAgent

from ..config import MODEL_FLASH
from ..tools.google_ads_keywords import generate_keyword_ideas, get_keyword_forecasts, get_search_volume
from ..tools.competitor_tools import analyze_competitor_ads, get_auction_insights, competitor_landing_pages
from ..tools.trend_tools import get_google_trends, get_industry_news


keyword_research_agent = Agent(
    name="keyword_research_agent",
    model=MODEL_FLASH,
    description="Performs keyword research using Google Ads Keyword Planner.",
    instruction="""You are a keyword research specialist. Using the campaign brief from {app:campaign_brief}:

1. Call generate_keyword_ideas ONCE with ALL the seed keywords combined into a single list
2. Do NOT call any other tools — generate_keyword_ideas already returns volume, competition, and CPC data
3. From the results, organize the top keywords by relevance to the client's business

IMPORTANT: Make exactly ONE tool call. Do NOT call get_search_volume or get_keyword_forecasts.

Present a CONCISE keyword plan (MAX 400 words) as bullet points:
- Top 15 keywords with: volume, CPC range, competition level, recommended match type
- Brief 2-3 line summary of the keyword landscape
- No long paragraphs. Bullet points only.
""",
    tools=[generate_keyword_ideas],
    output_key="app:keyword_plan",
)

competitor_research_agent = Agent(
    name="competitor_research_agent",
    model=MODEL_FLASH,
    description="Analyzes competitor ads, landing pages, and auction positioning.",
    instruction="""You are a competitive intelligence analyst for Google Ads. Using {app:campaign_brief}:

1. Pick the TOP 2 most important seed keywords and call analyze_competitor_ads for each (max 2 calls)
2. Call competitor_landing_pages ONCE for the primary keyword only
3. Do NOT use get_auction_insights unless a specific campaign_id is available in the brief

IMPORTANT: Limit yourself to a MAXIMUM of 3 tool calls total to avoid overloading the APIs.

From the results, identify:
   - Who the top advertisers are for these keywords
   - What headlines and descriptions competitors use
   - What offers/promotions competitors highlight
   - Gaps in competitor messaging we can exploit

Compile a CONCISE competitor intel report (MAX 400 words). Use bullet points, no long paragraphs.
""",
    tools=[analyze_competitor_ads, get_auction_insights, competitor_landing_pages],
    output_key="app:competitor_intel",
)

trend_detection_agent = Agent(
    name="trend_detection_agent",
    model=MODEL_FLASH,
    description="Detects trending topics and emerging opportunities using Google Trends and news.",
    instruction="""You are a trend analyst. Using the campaign brief from {app:campaign_brief}:

1. Call get_google_trends for the TOP 2 most important seed keywords ONLY (max 2 calls)
2. Call get_industry_news ONCE with the main business topic/industry

IMPORTANT: Limit yourself to a MAXIMUM of 3 tool calls total. Do NOT check every keyword — focus on the top 2.

From the results, identify:
   - Whether key terms have rising, stable, or declining interest
   - Related trending queries worth targeting
   - Any news-driven opportunities
   - Seasonal patterns if visible

Present findings as a CONCISE report (MAX 300 words). Use bullet points, no long paragraphs.
""",
    tools=[get_google_trends, get_industry_news],
    output_key="app:trend_data",
)

research_pipeline = SequentialAgent(
    name="research_pipeline",
    description="Runs keyword research, then competitor analysis, then trend detection sequentially.",
    sub_agents=[keyword_research_agent, competitor_research_agent, trend_detection_agent],
)
