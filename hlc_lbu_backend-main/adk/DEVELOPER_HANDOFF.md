# Google Search Ads Multi-Agent System - Developer Handoff Documentation

**Project:** Google Ads ADK Multi-Agent System
**Version:** 1.0.0
**Date:** March 2026
**Stack:** Google ADK v1.26.0 | Python 3.11 | Google Ads API v23 | Gemini Models

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Environment Setup](#3-environment-setup)
4. [Folder Structure](#4-folder-structure)
5. [Configuration](#5-configuration)
6. [Agent Pipelines (Detailed)](#6-agent-pipelines-detailed)
7. [Tool Functions (All 28)](#7-tool-functions-all-28)
8. [Pydantic Schemas](#8-pydantic-schemas)
9. [Prompt System](#9-prompt-system)
10. [Session State & Data Flow](#10-session-state--data-flow)
11. [Critical Fixes & Gotchas](#11-critical-fixes--gotchas)
12. [Running the System](#12-running-the-system)
13. [Testing Checklist](#13-testing-checklist)
14. [Known Limitations & Next Steps](#14-known-limitations--next-steps)

---

## 1. System Overview

This is a **full-lifecycle Google Search Ads management system** built as a multi-agent team using the Google Agent Development Kit (ADK). It handles:

- **Client Onboarding** - Structured 15-question interview to build a campaign brief
- **Market Research** - Keyword research, competitor analysis, and trend detection
- **Campaign Creation** - Strategy design, ad copy generation, and API deployment
- **Performance Optimization** - Automated monitoring, diagnosis, and bid/budget adjustments
- **Reporting** - On-demand performance reports with actionable insights
- **Experimentation** - A/B test proposals and management

The system uses the **Google Ads API v23** for all campaign operations and **Gemini models** (via Google ADK) for agent intelligence.

### Current Account Configuration

| Parameter | Value |
|-----------|-------|
| MCC (Login Customer ID) | `2664438976` |
| Client Account (Customer ID) | `4453673050` |
| Account Currency | MXN (Mexican Pesos) |
| Test Business | Hi Luca MX |
| Target Market | Mexico |

---

## 2. Architecture

```
root_agent (LlmAgent - Router, gemini-3-flash-preview)
  |
  |-- intake_pipeline (SequentialAgent)
  |     |-- voice_intake_agent       (gemini-3-flash-preview)
  |     +-- brief_compiler_agent     (gemini-2.5-flash)
  |
  |-- research_pipeline (SequentialAgent)
  |     |-- keyword_research_agent   (gemini-3-flash-preview)
  |     |-- competitor_research_agent (gemini-3-flash-preview)
  |     +-- trend_detection_agent    (gemini-3-flash-preview)
  |
  |-- campaign_builder_pipeline (SequentialAgent)
  |     |-- strategy_agent           (gemini-3.1-pro-preview)
  |     |-- ad_copy_agent            (gemini-3.1-pro-preview)
  |     +-- implementation_agent     (gemini-3-flash-preview)
  |
  |-- optimization_loop (LoopAgent, max_iterations=5)
  |     |-- monitor_agent            (gemini-3-flash-preview)
  |     |-- diagnosis_agent          (gemini-3.1-pro-preview)
  |     |-- action_agent             (gemini-3-flash-preview)
  |     +-- checkpoint_agent         (gemini-2.5-flash)
  |
  |-- reporting_agent                (gemini-3-flash-preview)
  |
  +-- experiment_agent               (gemini-2.5-pro)
```

### Agent Type Breakdown

| ADK Type | Usage | Behavior |
|----------|-------|----------|
| `Agent` (LlmAgent) | All individual agents | AI-powered with tools and instructions |
| `SequentialAgent` | intake, research, campaign_builder | Runs sub-agents in order, one after another |
| `LoopAgent` | optimization_loop | Repeats sub-agents up to `max_iterations` |

### Why SequentialAgent for Research?
The research pipeline was **changed from ParallelAgent to SequentialAgent** because concurrent HTTP calls from three research agents overwhelmed the ADK SSE (Server-Sent Events) web connection, causing `TypeError: Load failed` crashes. Sequential execution is stable.

---

## 3. Environment Setup

### Prerequisites

- Python 3.11+
- Virtual environment at `.venv`
- Google ADK v1.26.0 (`pip install google-adk`)
- Google Ads Python library v29.2.0 (`pip install google-ads==29.2.0`)

### Required .env Variables

Create a `.env` file in `/Users/imac/Google-ADK/google_ads_agents/`:

```env
# Gemini API
GOOGLE_API_KEY=<your-gemini-api-key>

# Google Ads API
GOOGLE_ADS_DEVELOPER_TOKEN=<developer-token-from-mcc>
GOOGLE_ADS_CLIENT_ID=<oauth-client-id>
GOOGLE_ADS_CLIENT_SECRET=<oauth-client-secret>
GOOGLE_ADS_REFRESH_TOKEN=<oauth-refresh-token>
GOOGLE_ADS_LOGIN_CUSTOMER_ID=<mcc-account-id-no-dashes>
GOOGLE_ADS_CUSTOMER_ID=<client-account-id-no-dashes>

# External APIs
SERPAPI_KEY=<serpapi-api-key>
NEWSAPI_KEY=<newsapi-api-key>
```

| Key | Source | Free Tier |
|-----|--------|-----------|
| `GOOGLE_API_KEY` | aistudio.google.com/apikey | Yes |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads MCC > API Center | Yes (test account) |
| `GOOGLE_ADS_CLIENT_ID` / `CLIENT_SECRET` | Google Cloud Console > OAuth | Yes |
| `GOOGLE_ADS_REFRESH_TOKEN` | Generated via OAuth flow | Yes |
| `SERPAPI_KEY` | serpapi.com | 100 searches/month |
| `NEWSAPI_KEY` | newsapi.org | 100 requests/day |

### Google Ads API Authentication

The system uses `GoogleAdsClient.load_from_dict()` with OAuth2 refresh tokens. The configuration includes:
- `use_proto_plus: True` (required for protobuf 4+ compatibility)
- `version: "v23"` (Google Ads API version)
- `login_customer_id` for MCC-level authentication (dashes are stripped automatically)

---

## 4. Folder Structure

```
/Users/imac/Google-ADK/google_ads_agents/
|-- __init__.py                    # Global model override + module import
|-- agent.py                       # Root agent (router) definition
|-- config.py                      # Model tier constants
|-- .env                           # API keys (not committed)
|
|-- agents/                        # Agent pipeline definitions
|   |-- __init__.py
|   |-- intake.py                  # intake_pipeline (SequentialAgent)
|   |-- research.py                # research_pipeline (SequentialAgent)
|   |-- campaign_builder.py        # campaign_builder_pipeline (SequentialAgent)
|   |-- optimization.py            # optimization_loop (LoopAgent)
|   |-- reporting.py               # reporting_agent
|   +-- experiment.py              # experiment_agent
|
|-- tools/                         # Tool functions (28 total)
|   |-- __init__.py
|   |-- shared_utils.py            # Google Ads client factory, helpers
|   |-- google_ads_keywords.py     # 3 functions: keyword ideas, forecasts, volume
|   |-- google_ads_campaigns.py    # 5 functions: campaign, ad group, keywords, RSA, negatives
|   |-- google_ads_reporting.py    # 4 functions: campaign/keyword/search term/ad performance
|   |-- google_ads_optimization.py # 6 functions: recommendations, bids, budgets, pauses, strategy
|   |-- google_ads_assets.py       # 1 function: ad copy validation
|   |-- competitor_tools.py        # 3 functions: competitor ads, auction insights, landing pages
|   |-- trend_tools.py             # 2 functions: Google Trends, industry news
|   +-- experiment_tools.py        # 3 functions: drafts, experiments, results
|
|-- prompts/                       # Agent instruction templates
|   |-- __init__.py
|   |-- intake_prompt.py           # VOICE_INTAKE_INSTRUCTION, BRIEF_COMPILER_INSTRUCTION
|   |-- strategy_prompt.py         # STRATEGY_INSTRUCTION, AD_COPY_INSTRUCTION, IMPLEMENTATION_INSTRUCTION
|   |-- optimization_prompt.py     # MONITOR, DIAGNOSIS, ACTION, CHECKPOINT instructions
|   +-- reporting_prompt.py        # REPORTING_INSTRUCTION, EXPERIMENT_INSTRUCTION
|
+-- schemas/                       # Pydantic data models
    |-- __init__.py
    |-- campaign_brief.py          # CampaignBrief, TargetAudience
    |-- campaign_structure.py      # CampaignStructure, CampaignPlan, AdGroupPlan, KeywordEntry
    |-- performance_report.py      # PerformanceReport, CampaignMetrics, KeywordMetrics
    +-- experiment_proposal.py     # ExperimentProposal
```

---

## 5. Configuration

### `config.py` - Model Tiers

```python
MODEL_PRO   = "gemini-3.1-pro-preview"  # Strategy, ad copy, diagnosis
MODEL_FLASH = "gemini-3-flash-preview"  # Most agents (fast, capable)
MODEL_STD   = "gemini-2.5-flash"        # Brief compiler, checkpoint
MODEL_EXP   = "gemini-2.5-pro"          # Experiment agent
MODEL = MODEL_FLASH                      # Legacy alias
```

### `__init__.py` - Global Model Override

```python
from google.adk.agents.llm_agent import LlmAgent
LlmAgent.set_default_model("gemini-3-flash-preview")
from . import agent
```

This ensures ALL agents default to `gemini-3-flash-preview` unless they explicitly specify a different model.

### Model Assignment by Agent

| Agent | Model | Reason |
|-------|-------|--------|
| root_agent | MODEL (Flash) | Fast routing |
| voice_intake_agent | MODEL_FLASH | Conversational, fast |
| brief_compiler_agent | MODEL_STD | Structured extraction |
| keyword_research_agent | MODEL_FLASH | Tool calling |
| competitor_research_agent | MODEL_FLASH | Tool calling |
| trend_detection_agent | MODEL_FLASH | Tool calling |
| strategy_agent | MODEL_PRO | Complex strategic decisions |
| ad_copy_agent | MODEL_PRO | Creative writing quality |
| implementation_agent | MODEL_FLASH | Sequential API calls |
| monitor_agent | MODEL_FLASH | Data retrieval |
| diagnosis_agent | MODEL_PRO | Complex analysis |
| action_agent | MODEL_FLASH | API execution |
| checkpoint_agent | MODEL_STD | Simple decision logic |
| reporting_agent | MODEL_FLASH | Data formatting |
| experiment_agent | MODEL_EXP | Experimental reasoning |

---

## 6. Agent Pipelines (Detailed)

### 6.1 Intake Pipeline (`agents/intake.py`)

**Type:** `SequentialAgent`
**Purpose:** Onboard new clients through a structured interview.

```
voice_intake_agent --> brief_compiler_agent
```

**voice_intake_agent**
- Model: `gemini-3-flash-preview`
- Conducts a 15-question interview across 4 phases:
  - Phase 1: Business Context (questions 1-4)
  - Phase 2: Goals & Budget (questions 5-8)
  - Phase 3: Campaign Specifics (questions 9-12)
  - Phase 4: Messaging (questions 13-15)
- Asks ONE question at a time, waits for response
- Output key: `app:intake_raw_transcript`

**brief_compiler_agent**
- Model: `gemini-2.5-flash`
- Reads `{app:intake_raw_transcript}` and extracts structured data
- Output key: `app:campaign_brief`
- Output schema: `CampaignBrief` (Pydantic model)
- Extracts: business_name, product_description, website_url, competitors, target_audience, primary_goal, monthly_budget, cac_target, cpa_target, seed_keywords, negative_keywords, geo_targets, geo_exclusions, ad_schedule, unique_selling_point, current_offers, desired_action

---

### 6.2 Research Pipeline (`agents/research.py`)

**Type:** `SequentialAgent` (was ParallelAgent, changed for SSE stability)
**Requires:** `app:campaign_brief` must exist

```
keyword_research_agent --> competitor_research_agent --> trend_detection_agent
```

**keyword_research_agent**
- Model: `gemini-3-flash-preview`
- Tools: `generate_keyword_ideas` (1 tool call only)
- Makes ONE call with ALL seed keywords combined
- Does NOT call `get_search_volume` or `get_keyword_forecasts`
- Output key: `app:keyword_plan`
- Returns top 15 keywords with volume, CPC, competition, match type recommendation

**competitor_research_agent**
- Model: `gemini-3-flash-preview`
- Tools: `analyze_competitor_ads`, `get_auction_insights`, `competitor_landing_pages`
- Max 3 tool calls total:
  - `analyze_competitor_ads` x2 (top 2 keywords)
  - `competitor_landing_pages` x1 (primary keyword)
- Output key: `app:competitor_intel`

**trend_detection_agent**
- Model: `gemini-3-flash-preview`
- Tools: `get_google_trends`, `get_industry_news`
- Max 3 tool calls total:
  - `get_google_trends` x2 (top 2 keywords)
  - `get_industry_news` x1 (main industry topic)
- Output key: `app:trend_data`

---

### 6.3 Campaign Builder Pipeline (`agents/campaign_builder.py`)

**Type:** `SequentialAgent`
**Requires:** `app:campaign_brief`, `app:keyword_plan`, `app:competitor_intel`

```
strategy_agent --> ad_copy_agent --> implementation_agent
```

**strategy_agent**
- Model: `gemini-3.1-pro-preview`
- No tools (pure reasoning)
- Reads: `campaign_brief`, `keyword_plan`, `competitor_intel`, `trend_data`
- Designs campaign structure: campaigns, ad groups, keywords, bidding strategy
- Output key: `app:campaign_structure`
- Output schema: `CampaignStructure`
- **CRITICAL:** Always uses `MANUAL_CPC` unless client confirms conversion tracking

**ad_copy_agent**
- Model: `gemini-3.1-pro-preview`
- Tools: `validate_ad_copy`
- Generates per ad group: 15 headlines (max 30 chars) + 4 descriptions (max 90 chars)
- Follows 10 copywriting rules (keyword inclusion, USP, CTAs, etc.)
- Output key: `app:ad_copy_variants`

**implementation_agent**
- Model: `gemini-3-flash-preview`
- Tools: `create_campaign`, `create_ad_group`, `add_keywords`, `create_responsive_search_ad`, `add_negative_keywords`
- Follows strict execution order:
  1. Create campaigns with budget + bidding
  2. Create ad groups with CPC bids
  3. Add keywords with match types
  4. Create RSAs with headlines/descriptions
  5. Add negative keywords
- Output key: `app:campaign_ids`
- **Campaigns are created in PAUSED status** for review

---

### 6.4 Optimization Loop (`agents/optimization.py`)

**Type:** `LoopAgent` (max 5 iterations)
**Requires:** Active campaigns with `app:campaign_ids`

```
monitor_agent --> diagnosis_agent --> action_agent --> checkpoint_agent
                                                            |
                                                   (exit_loop or continue)
```

**monitor_agent**
- Model: `gemini-3-flash-preview`
- Tools: All 4 reporting tools
- Pulls: campaign performance, keyword performance, search term report
- Compares CPA/CAC against targets
- Output key: `app:performance_snapshot`

**diagnosis_agent**
- Model: `gemini-3.1-pro-preview`
- No tools (pure analysis)
- Categorizes issues: Critical (pause), High (reduce bids), Medium (adjust), Opportunity (increase)
- Output key: `app:diagnosis_result`

**action_agent**
- Model: `gemini-3-flash-preview`
- Tools: `get_recommendations`, `apply_recommendation`, `update_keyword_bid`, `update_campaign_budget`, `pause_keyword`, `update_bidding_strategy`, `add_negative_keywords`
- Safety guardrails: max 50% bid change, max 30% budget change, max 20 keyword pauses per cycle
- Output key: `app:optimization_log`

**checkpoint_agent**
- Model: `gemini-2.5-flash`
- No tools
- Exits loop when: all campaigns below CPA target AND budget pacing OK AND no critical changes made
- Always exits at iteration 5 (safety cap)
- Output key: `app:optimization_checkpoint`

---

### 6.5 Reporting Agent (`agents/reporting.py`)

**Type:** Single `Agent`
- Model: `gemini-3-flash-preview`
- Tools: `get_campaign_performance`, `get_keyword_performance`, `get_search_term_report`, `get_ad_performance`
- Generates structured reports: Executive Summary, Campaign Table, Top/Bottom Keywords, Search Term Insights, Recommendations, Budget Pacing

---

### 6.6 Experiment Agent (`agents/experiment.py`)

**Type:** Single `Agent`
- Model: `gemini-2.5-pro`
- Tools: `get_campaign_performance`, `get_keyword_performance`, `analyze_competitor_ads`, `get_google_trends`, `get_industry_news`, `create_campaign_draft`, `create_experiment`, `get_experiment_results`
- Proposes 3-5 experiments ranked by expected impact
- Types: Ad copy tests, bidding strategy tests, keyword expansion, audience/targeting tests

---

### Root Agent Routing Rules (`agent.py`)

The root agent uses these routing rules:
1. Always start with `intake_pipeline` for new clients
2. After intake, suggest `research_pipeline`
3. After research, summarize findings and ASK user before proceeding
4. Only transfer to `campaign_builder_pipeline` on explicit user confirmation
5. Use `optimization_loop` once campaigns have run a few days
6. Use `reporting_agent` for any performance questions
7. Use `experiment_agent` for improvement ideas
8. **NEVER auto-chain pipelines** - always get user confirmation between steps

---

## 7. Tool Functions (All 28)

### 7.1 Shared Utilities (`tools/shared_utils.py`)

| Function | Purpose |
|----------|---------|
| `get_google_ads_client()` | Returns cached `GoogleAdsClient` instance (singleton pattern) |
| `get_customer_id()` | Returns customer ID from `.env` (strips dashes) |
| `micros_to_currency(micros)` | Converts Google Ads micros to dollars/pesos |
| `currency_to_micros(dollars)` | Converts dollars/pesos to micros |

**Client initialization:**
```python
config = {
    "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
    "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
    "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", ""),
    "use_proto_plus": True,
}
_client_cache = GoogleAdsClient.load_from_dict(config, version="v23")
```

---

### 7.2 Keyword Research Tools (`tools/google_ads_keywords.py`) - 3 Functions

| Function | API | Parameters | Returns |
|----------|-----|------------|---------|
| `generate_keyword_ideas` | KeywordPlanIdeaService.GenerateKeywordIdeas | `seed_keywords`, `url`, `language_id` (default "1000"), `geo_target_id` (default "2840"), `num_results` | Keywords + avg_monthly_searches + competition + bid estimates |
| `get_keyword_forecasts` | KeywordPlanIdeaService.GenerateKeywordForecastMetrics | `keywords`, `monthly_budget`, `geo_target_id`, `language_id` | Projected clicks, impressions, cost, CTR, CPC per keyword |
| `get_search_volume` | KeywordPlanIdeaService.GenerateKeywordHistoricalMetrics | `keywords`, `geo_target_id`, `language_id` | Monthly volume history (last 12 months), competition |

**Default geo target:** `2840` (United States). For Mexico, use `2484`.
**Default language:** `1000` (English). For Spanish, use `1003`.

---

### 7.3 Campaign Management Tools (`tools/google_ads_campaigns.py`) - 5 Functions

| Function | API | Key Parameters |
|----------|-----|----------------|
| `create_campaign` | CampaignService + CampaignBudgetService | `name`, `daily_budget`, `bidding_strategy` (default "MANUAL_CPC"), `bidding_target_value`, `network`, `start_date`, `end_date` |
| `create_ad_group` | AdGroupService | `campaign_id`, `name`, `cpc_bid` (default 2.0) |
| `add_keywords` | AdGroupCriterionService | `ad_group_id`, `keywords` (list of dicts with `text` and `match_type`) |
| `create_responsive_search_ad` | AdGroupAdService | `ad_group_id`, `headlines` (list, max 15), `descriptions` (list, max 4), `final_url` |
| `add_negative_keywords` | CampaignCriterionService | `campaign_id`, `keywords` (list of strings) |

**Critical implementation details in `create_campaign`:**

```python
# Budget must NOT be shared
budget.explicitly_shared = False

# EU political advertising field (required in API v23+)
campaign.contains_eu_political_advertising = (
    client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
)

# Campaigns always start PAUSED
campaign.status = client.enums.CampaignStatusEnum.PAUSED

# Bidding strategy handling
if bidding_strategy == "MANUAL_CPC":
    campaign.manual_cpc.enhanced_cpc_enabled = False
elif bidding_strategy == "MAXIMIZE_CONVERSIONS":
    campaign.maximize_conversions.target_cpa_micros = 0
elif bidding_strategy == "TARGET_CPA":
    campaign.maximize_conversions.target_cpa_micros = currency_to_micros(bidding_target_value)
elif bidding_strategy == "MAXIMIZE_CONVERSION_VALUE":
    campaign.maximize_conversion_value.target_roas = 0
elif bidding_strategy == "TARGET_ROAS":
    campaign.maximize_conversion_value.target_roas = bidding_target_value
```

**Critical implementation details in `create_responsive_search_ad`:**

```python
# Protobuf 4+ requires get_type() + append() pattern
for headline in headlines[:15]:
    asset = client.get_type("AdTextAsset")
    asset.text = headline[:30]
    ad.responsive_search_ad.headlines.append(asset)

for description in descriptions[:4]:
    asset = client.get_type("AdTextAsset")
    asset.text = description[:90]
    ad.responsive_search_ad.descriptions.append(asset)
```

---

### 7.4 Reporting Tools (`tools/google_ads_reporting.py`) - 4 Functions

All use GAQL (Google Ads Query Language) via `GoogleAdsService.search_stream()`.

| Function | GAQL View | Returns |
|----------|-----------|---------|
| `get_campaign_performance(campaign_ids, date_range)` | `campaign` | Impressions, clicks, cost, conversions, CTR, CPC, CPA per campaign |
| `get_keyword_performance(campaign_id, date_range, limit)` | `keyword_view` | Per-keyword metrics + quality score |
| `get_search_term_report(campaign_id, date_range, limit)` | `search_term_view` | Actual search queries + metrics |
| `get_ad_performance(ad_group_id, date_range)` | `ad_group_ad` | Per-ad metrics including RSA headlines |

**Date range options:** `LAST_7_DAYS`, `LAST_30_DAYS`, `THIS_MONTH`, `LAST_MONTH`, or custom `YYYY-MM-DD,YYYY-MM-DD`

---

### 7.5 Optimization Tools (`tools/google_ads_optimization.py`) - 6 Functions

| Function | API | Purpose |
|----------|-----|---------|
| `get_recommendations(campaign_id)` | RecommendationService GAQL | Get Google's optimization suggestions |
| `apply_recommendation(resource_name)` | RecommendationService.Apply | Apply a recommendation |
| `update_keyword_bid(ad_group_id, criterion_id, new_cpc_bid)` | AdGroupCriterionService.Mutate | Change keyword CPC bid |
| `update_campaign_budget(budget_resource_name, new_daily_budget)` | CampaignBudgetService.Mutate | Change daily budget |
| `pause_keyword(ad_group_id, criterion_id)` | AdGroupCriterionService.Mutate | Pause a keyword |
| `update_bidding_strategy(campaign_id, strategy_type, target_value)` | CampaignService.Mutate | Change bidding strategy |

All mutation functions use `FieldMask` for partial updates.

---

### 7.6 Ad Copy Validation (`tools/google_ads_assets.py`) - 1 Function

| Function | Purpose |
|----------|---------|
| `validate_ad_copy(headlines, descriptions)` | Validates RSA copy: headline max 30 chars, description max 90 chars, min 3 headlines, min 2 descriptions |

---

### 7.7 Competitor Tools (`tools/competitor_tools.py`) - 3 Functions

| Function | API | Parameters | Returns |
|----------|-----|------------|---------|
| `analyze_competitor_ads(query, num_results)` | SerpAPI (ads block) | Search query | Competitor ad copy, headlines, display URLs, sitelinks |
| `get_auction_insights(campaign_id)` | Google Ads GAQL (`auction_insight`) | Campaign ID | Impression share, overlap rate, outranking share per competitor |
| `competitor_landing_pages(query, num_results)` | SerpAPI (organic results) | Search query | Top organic URLs, titles, snippets |

All SerpAPI calls use `requests` library with **15-second timeouts** and explicit `Timeout` exception handling.

---

### 7.8 Trend Tools (`tools/trend_tools.py`) - 2 Functions

| Function | API | Parameters | Returns |
|----------|-----|------------|---------|
| `get_google_trends(keyword, timeframe)` | SerpAPI (google_trends engine) | Keyword, timeframe ("today 3-m") | Interest over time (last 12 points), rising queries (top 5), related queries (top 5) |
| `get_industry_news(topic, num_articles)` | NewsAPI | Topic, count (max 5) | Recent articles: title, source, date, description |

Both use `requests` with **15-second timeouts**. `get_google_trends` makes **2 SerpAPI calls** (timeseries + related queries).

---

### 7.9 Experiment Tools (`tools/experiment_tools.py`) - 3 Functions

| Function | API | Purpose |
|----------|-----|---------|
| `create_campaign_draft(base_campaign_id, draft_name)` | CampaignDraftService | Create a draft from existing campaign |
| `create_experiment(draft_resource_name, experiment_name, traffic_split_percent)` | ExperimentService | Launch an A/B test |
| `get_experiment_results(experiment_resource_name)` | GoogleAdsService GAQL (`experiment_arm`) | Get control vs experiment metrics |

---

## 8. Pydantic Schemas

### 8.1 CampaignBrief (`schemas/campaign_brief.py`)

```python
class TargetAudience(BaseModel):
    age_range: str           # e.g., "25-45"
    locations: list[str]     # Target geographic locations
    pain_points: str         # Main customer problems
    demographics_notes: str  # Additional notes (optional)

class CampaignBrief(BaseModel):
    business_name: str
    product_description: str
    website_url: str
    competitors: list[str]
    target_audience: TargetAudience
    primary_goal: str           # leads, sales, calls, other
    monthly_budget: float       # In account currency
    cac_target: float           # Max cost per customer
    cpa_target: float           # Max cost per lead/action
    seed_keywords: list[str]
    negative_keywords: list[str]  # Default: []
    geo_targets: list[str]
    geo_exclusions: list[str]     # Default: []
    ad_schedule: str              # Default: "all_day"
    unique_selling_point: str
    current_offers: str           # Default: ""
    desired_action: str           # form, call, buy
```

### 8.2 CampaignStructure (`schemas/campaign_structure.py`)

```python
class KeywordEntry(BaseModel):
    text: str           # Keyword text
    match_type: str     # BROAD, PHRASE, or EXACT

class AdGroupPlan(BaseModel):
    name: str           # Ad group name
    theme: str          # Target intent/theme
    keywords: list[KeywordEntry]
    cpc_bid: float      # Max CPC bid

class CampaignPlan(BaseModel):
    name: str
    daily_budget: float
    bidding_strategy: str        # MANUAL_CPC, etc.
    bidding_target_value: float  # Default: 0.0
    network: str                 # Default: "SEARCH"
    geo_targets: list[str]
    ad_schedule: str             # Default: "all_day"
    ad_groups: list[AdGroupPlan]
    negative_keywords: list[str]  # Default: []

class CampaignStructure(BaseModel):
    campaigns: list[CampaignPlan]
    rationale: str               # Strategy explanation
```

### 8.3 PerformanceReport (`schemas/performance_report.py`)

```python
class CampaignMetrics(BaseModel):
    campaign_name: str
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc: float = 0.0
    cpa: float = 0.0
    conversion_rate: float = 0.0

class KeywordMetrics(BaseModel):
    keyword: str
    match_type: str
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc: float = 0.0
    quality_score: int = 0

class PerformanceReport(BaseModel):
    date_range: str
    total_spend: float = 0.0
    total_conversions: float = 0.0
    overall_cpa: float = 0.0
    overall_ctr: float = 0.0
    campaigns: list[CampaignMetrics] = []
    top_keywords: list[KeywordMetrics] = []
    issues_found: list[str] = []
    recommendations: list[str] = []
```

### 8.4 ExperimentProposal (`schemas/experiment_proposal.py`)

```python
class ExperimentProposal(BaseModel):
    hypothesis: str             # "If we [change], then [outcome] because [reason]"
    test_type: str              # ad_copy, bidding, keyword, targeting, landing_page
    changes: list[str]          # Specific changes to implement
    duration_days: int = 14     # Test duration
    traffic_split_percent: int = 50
    success_metric: str         # CPA, CTR, conversion_rate
    risk_level: str             # low, medium, high
    expected_impact: str        # Expected improvement
    base_campaign_id: str = ""  # Campaign to base experiment on
```

---

## 9. Prompt System

### Prompt Files and Their Constants

| File | Constants | Used By |
|------|-----------|---------|
| `intake_prompt.py` | `VOICE_INTAKE_INSTRUCTION`, `BRIEF_COMPILER_INSTRUCTION` | voice_intake_agent, brief_compiler_agent |
| `strategy_prompt.py` | `STRATEGY_INSTRUCTION`, `AD_COPY_INSTRUCTION`, `IMPLEMENTATION_INSTRUCTION` | strategy_agent, ad_copy_agent, implementation_agent |
| `optimization_prompt.py` | `MONITOR_INSTRUCTION`, `DIAGNOSIS_INSTRUCTION`, `ACTION_INSTRUCTION`, `CHECKPOINT_INSTRUCTION` | 4 optimization loop agents |
| `reporting_prompt.py` | `REPORTING_INSTRUCTION`, `EXPERIMENT_INSTRUCTION` | reporting_agent, experiment_agent |

### Key Prompt Rules

**Strategy Prompt - Bidding:**
- ALWAYS use `MANUAL_CPC` for new campaigns
- NEVER use `MAXIMIZE_CONVERSIONS`, `TARGET_CPA`, `TARGET_ROAS` unless conversion tracking is confirmed
- Daily budget = monthly_budget / 30.4

**Implementation Prompt:**
- ALWAYS use `bidding_strategy="MANUAL_CPC"` unless campaign structure says otherwise
- Do NOT retry failed API calls more than once
- Follow strict creation order: campaigns > ad groups > keywords > RSAs > negatives

**Optimization Diagnosis Thresholds:**
- Critical: CPA > 2x target AND > $50 spend --> PAUSE
- High: CPA > 1.5x target --> reduce bid 20%
- Medium: CPA 1x-1.5x target --> reduce bid 10%
- Opportunity: CPA < 0.5x target --> increase bid

**Optimization Action Guardrails:**
- Max bid change: 50% per action
- Max budget change: 30% per action
- Max keyword pauses: 20 per cycle
- Max negative additions: 50 per cycle
- Never pause ALL keywords in an ad group

---

## 10. Session State & Data Flow

ADK session state variables are shared between agents using `output_key` and referenced in prompts with `{app:variable}`.

| State Key | Written By | Read By | Type |
|-----------|-----------|---------|------|
| `app:intake_raw_transcript` | voice_intake_agent | brief_compiler_agent | str |
| `app:campaign_brief` | brief_compiler_agent | research agents, strategy, ad_copy | JSON (CampaignBrief) |
| `app:keyword_plan` | keyword_research_agent | strategy, ad_copy | str (formatted) |
| `app:competitor_intel` | competitor_research_agent | strategy, ad_copy | str (formatted) |
| `app:trend_data` | trend_detection_agent | strategy, experiment | str (formatted) |
| `app:campaign_structure` | strategy_agent | ad_copy, implementation | JSON (CampaignStructure) |
| `app:ad_copy_variants` | ad_copy_agent | implementation | str (formatted) |
| `app:campaign_ids` | implementation_agent | optimization, reporting | str (IDs) |
| `app:performance_snapshot` | monitor_agent | diagnosis, action, checkpoint | str (formatted) |
| `app:diagnosis_result` | diagnosis_agent | action | str (formatted) |
| `app:optimization_log` | action_agent | checkpoint | str (formatted) |
| `app:optimization_checkpoint` | checkpoint_agent | loop controller | str |
| `app:cpa_target` | brief_compiler_agent | monitor, checkpoint | float |
| `app:cac_target` | brief_compiler_agent | monitor, checkpoint | float |
| `app:monthly_budget` | brief_compiler_agent | diagnosis, reporting | float |

---

## 11. Critical Fixes & Gotchas

These are issues that were discovered and fixed during development. **Do not revert these.**

### Fix 1: EU Political Advertising Field (API v23+)

**Problem:** `create_campaign` failed with `INVALID_ARGUMENT` because `contains_eu_political_advertising` is a required field.

**Wrong approach (boolean):**
```python
campaign.contains_eu_political_advertising = False  # DOES NOT WORK
```

**Correct fix (enum):**
```python
campaign.contains_eu_political_advertising = (
    client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
)
```

### Fix 2: Bidding Strategy - MANUAL_CPC Default

**Problem:** `MAXIMIZE_CONVERSIONS`, `TARGET_CPA`, and `TARGET_ROAS` all fail if the Google Ads account does not have conversion tracking enabled.

**Fix:** Changed default from `MAXIMIZE_CONVERSIONS` to `MANUAL_CPC` in:
- `create_campaign()` function signature
- `STRATEGY_INSTRUCTION` prompt
- `IMPLEMENTATION_INSTRUCTION` prompt

### Fix 3: Shared Budget Incompatibility

**Problem:** `BIDDING_STRATEGY_TYPE_INCOMPATIBLE_WITH_SHARED_BUDGET` error when creating budgets.

**Fix:** Added `budget.explicitly_shared = False` to the budget creation block.

### Fix 4: RSA Creation - Protobuf 4+ Compatibility

**Problem:** `.add()` method doesn't exist on repeated composite fields in protobuf 4+. Error: `'RepeatedComposite' object has no attribute 'add'`

**Wrong approach:**
```python
headline = ad.responsive_search_ad.headlines.add()  # DOES NOT WORK
headline.text = "..."
```

**Correct fix:**
```python
asset = client.get_type("AdTextAsset")
asset.text = "..."
ad.responsive_search_ad.headlines.append(asset)
```

### Fix 5: SSE Stream Crashes with ParallelAgent

**Problem:** Running keyword research, competitor analysis, and trend detection in parallel caused `TypeError: Load failed` due to too many concurrent HTTP calls overwhelming the ADK SSE connection.

**Fix:** Changed `research_pipeline` from `ParallelAgent` to `SequentialAgent`.

### Fix 6: MCC Authentication

**Problem:** `PERMISSION_DENIED` when making API calls.

**Fix:** Added `login_customer_id` to the client configuration for MCC-level auth. The `GOOGLE_ADS_LOGIN_CUSTOMER_ID` env var must be set to the MCC account ID.

---

## 12. Running the System

### Start the ADK Web Interface

```bash
cd /Users/imac/Google-ADK
source .venv/bin/activate
adk web
```

Then select `google_ads_agents` from the agent dropdown in the web interface.

### Typical User Flow

1. **"I have a new client"** --> Triggers `intake_pipeline`
   - System asks 15 questions
   - Produces structured `CampaignBrief`

2. **"Run the research"** --> Triggers `research_pipeline`
   - Keyword research (1 API call)
   - Competitor analysis (3 API calls)
   - Trend detection (3 API calls)
   - Produces: keyword_plan, competitor_intel, trend_data

3. **"Build the campaigns"** --> Triggers `campaign_builder_pipeline`
   - Strategy agent designs structure (MANUAL_CPC default)
   - Ad copy agent writes 15 headlines + 4 descriptions per ad group
   - Implementation agent creates everything via Google Ads API
   - Campaigns created in PAUSED status

4. **"Optimize the campaigns"** --> Triggers `optimization_loop`
   - Monitors performance vs targets
   - Diagnoses issues (4-tier priority)
   - Executes fixes with safety guardrails
   - Loops up to 5 times or until all targets met

5. **"How are we doing?"** --> Triggers `reporting_agent`
   - Pulls GAQL reports
   - Formats executive summary + detailed tables

6. **"What should we test?"** --> Triggers `experiment_agent`
   - Proposes 3-5 ranked experiments
   - Can create campaign drafts and A/B tests

### Voice Mode

For voice-based intake, use:
```bash
adk run --live google_ads_agents
```

---

## 13. Testing Checklist

### Environment Validation
- [ ] `.env` file has all required keys
- [ ] `adk web` starts without import errors
- [ ] Agent dropdown shows `google_ads_agents`

### Intake Pipeline
- [ ] Voice intake asks all 15 questions sequentially
- [ ] Brief compiler produces valid CampaignBrief JSON
- [ ] Session state `app:campaign_brief` is populated

### Research Pipeline
- [ ] `generate_keyword_ideas` returns real data from Keyword Planner
- [ ] `analyze_competitor_ads` returns competitor ad copy via SerpAPI
- [ ] `get_google_trends` returns trend data without timeout
- [ ] No SSE crashes during sequential execution
- [ ] All three output keys populated: `keyword_plan`, `competitor_intel`, `trend_data`

### Campaign Builder Pipeline
- [ ] Strategy agent uses MANUAL_CPC bidding
- [ ] Ad copy agent produces 15 headlines (<=30 chars) + 4 descriptions (<=90 chars) per ad group
- [ ] `create_campaign` succeeds (check: `contains_eu_political_advertising` enum, `explicitly_shared = False`)
- [ ] `create_ad_group` succeeds
- [ ] `add_keywords` succeeds with correct match types
- [ ] `create_responsive_search_ad` succeeds (check: `AdTextAsset` + `append()` pattern)
- [ ] `add_negative_keywords` succeeds
- [ ] Campaigns created in PAUSED status
- [ ] All campaign/ad group IDs captured in `app:campaign_ids`

### Reporting
- [ ] `get_campaign_performance` returns valid GAQL results
- [ ] `get_keyword_performance` includes quality scores
- [ ] `get_search_term_report` shows actual search queries
- [ ] Date range filtering works (preset and custom)

### Optimization Loop
- [ ] Monitor pulls fresh data
- [ ] Diagnosis correctly categorizes issues by priority
- [ ] Action agent respects safety guardrails
- [ ] Loop exits when targets met or at iteration 5
- [ ] No infinite loops

### Experiment Agent
- [ ] Proposes meaningful experiments
- [ ] `create_campaign_draft` works
- [ ] `create_experiment` works

---

## 14. Known Limitations & Next Steps

### Current Limitations

1. **No Conversion Tracking Integration** - The system defaults to MANUAL_CPC because conversion tracking setup is not automated. To use smart bidding (TARGET_CPA, MAXIMIZE_CONVERSIONS), conversion tracking must be manually configured in the Google Ads account first.

2. **Geo Targeting Defaults** - `generate_keyword_ideas` defaults to US (geo_target_id=2840) and English (language_id=1000). For Mexico, agents should pass `geo_target_id=2484` and `language_id=1003` (Spanish). This is not automated yet.

3. **Currency Handling** - All `currency_to_micros` / `micros_to_currency` functions label values as "dollars" but the account uses MXN. The math is correct (micros are currency-agnostic), but documentation/variable names are misleading.

4. **SerpAPI Rate Limits** - Free tier allows 100 searches/month. Research pipeline uses 5-7 calls per run, limiting total research runs.

5. **No Ad Schedule Implementation** - The `ad_schedule` field is captured in the brief but not implemented in campaign creation. Ad scheduling would require `CampaignCriterionService` with `AdScheduleInfo`.

6. **No Geographic Targeting Implementation** - `geo_targets` from the brief are not applied during campaign creation. Would need `CampaignCriterionService` with `LocationInfo`.

### Recommended Next Steps

1. **Add conversion tracking setup tools** - Create tools to set up conversion actions via the Google Ads API, enabling smart bidding strategies.

2. **Implement geo targeting** - Add geographic targeting to `create_campaign` using `CampaignCriterionService`.

3. **Implement ad scheduling** - Apply the `ad_schedule` from the brief as campaign criteria.

4. **Localize for Mexico** - Update default `geo_target_id` and `language_id` based on campaign brief locale. Add Spanish language support for ad copy generation.

5. **Add error recovery** - Implement retry logic with exponential backoff for transient API failures.

6. **Add campaign enable tool** - Create a tool to change campaign status from PAUSED to ENABLED after review.

7. **Dashboard integration** - Build a real-time dashboard showing campaign performance vs targets.

8. **Webhook notifications** - Add alerting when CPA exceeds targets or budgets are exhausted.

---

## Appendix: Complete File Listing (30 files)

```
google_ads_agents/__init__.py
google_ads_agents/agent.py
google_ads_agents/config.py
google_ads_agents/agents/__init__.py
google_ads_agents/agents/intake.py
google_ads_agents/agents/research.py
google_ads_agents/agents/campaign_builder.py
google_ads_agents/agents/optimization.py
google_ads_agents/agents/reporting.py
google_ads_agents/agents/experiment.py
google_ads_agents/tools/__init__.py
google_ads_agents/tools/shared_utils.py
google_ads_agents/tools/google_ads_keywords.py
google_ads_agents/tools/google_ads_campaigns.py
google_ads_agents/tools/google_ads_reporting.py
google_ads_agents/tools/google_ads_optimization.py
google_ads_agents/tools/google_ads_assets.py
google_ads_agents/tools/competitor_tools.py
google_ads_agents/tools/trend_tools.py
google_ads_agents/tools/experiment_tools.py
google_ads_agents/prompts/__init__.py
google_ads_agents/prompts/intake_prompt.py
google_ads_agents/prompts/strategy_prompt.py
google_ads_agents/prompts/optimization_prompt.py
google_ads_agents/prompts/reporting_prompt.py
google_ads_agents/schemas/__init__.py
google_ads_agents/schemas/campaign_brief.py
google_ads_agents/schemas/campaign_structure.py
google_ads_agents/schemas/performance_report.py
google_ads_agents/schemas/experiment_proposal.py
```
