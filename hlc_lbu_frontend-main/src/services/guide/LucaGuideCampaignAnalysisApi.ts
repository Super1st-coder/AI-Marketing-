import { handleCommonErrors } from "../common-errors";
import { $lucaGuideApi } from "@/utils/api";
import type { LucaGuideDashboardClassification } from "@/services/guide/LucaGuideDashboardApi";
import type { LucaGuideNorthStarPriority } from "@/services/guide/LucaGuideOnboardingApi";

export type LucaGuideCampaignAnalysisRequest = {
  date_range_start?: string;
  date_range_end?: string;
};

export type LucaGuideCampaignAnalysisNorthStarStatus = "behind" | "beating";

export type LucaGuideCampaignAnalysisNorthStarReading = {
  priority: LucaGuideNorthStarPriority;
  kpi: string;
  target: string;
  value: string;
  status: LucaGuideCampaignAnalysisNorthStarStatus;
  reading: string;
};

export type LucaGuideCampaignAnalysisPortfolioState = {
  winner: number;
  scalable: number;
  promising: number;
  losing: number;
  insufficient: number;
};

export type LucaGuideCampaignAnalysisPortfolioBreakdown = {
  state: LucaGuideDashboardClassification;
  label: string;
  count: number;
  spend: number;
  pct_spend: number;
};

export type LucaGuideCampaignAnalysisAdSetStates = {
  winner: number;
  scalable: number;
  promising: number;
  losing: number;
  "insufficient-data": number;
};

export type LucaGuideCampaignAnalysisAdSet = {
  name: string;
  ads: number;
  states: LucaGuideCampaignAnalysisAdSetStates;
  spend: number;
  results?: number;
  cost_per_result: number | null;
  reading: string;
};

export type LucaGuideCampaignAnalysisAdHighlight = {
  ad: string;
  state: LucaGuideDashboardClassification;
  ctr: string;
  spend: string;
};

export type LucaGuideCampaignAnalysisStats = {
  ads: number;
  spend?: number;
  impressions?: number;
  conversions?: number;
  winners?: number;
  losing?: number;
  winner_spend?: number;
  losing_spend?: number;
  objective?: string;
};

export type LucaGuideCampaignAnalysisContent = {
  headline: string;
  summary: string;
  objective_reading: string;
  portfolio_state: LucaGuideCampaignAnalysisPortfolioState;
  portfolio_breakdown?: LucaGuideCampaignAnalysisPortfolioBreakdown[];
  north_star_reading: LucaGuideCampaignAnalysisNorthStarReading[];
  constraint_synthesis: string;
  ad_sets: LucaGuideCampaignAnalysisAdSet[];
  working: LucaGuideCampaignAnalysisAdHighlight[];
  not_working: LucaGuideCampaignAnalysisAdHighlight[];
  stats: LucaGuideCampaignAnalysisStats;
};

export type LucaGuideCampaignAnalysis = {
  id: string;
  campaign_id: string;
  date_range_start: string | null;
  date_range_end: string | null;
  primary_kpi_key: string;
  primary_target: string;
  content: LucaGuideCampaignAnalysisContent;
  is_stale: boolean;
  created_at: string;
};

export default {
  async generate(
    campaignId: string,
    payload: LucaGuideCampaignAnalysisRequest = {},
  ): Promise<LucaGuideCampaignAnalysis> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignAnalysis>(
        `/api/v2/campaigns/${campaignId}/analysis`,
        {
          method: "POST",
          body: payload,
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async list(campaignId: string): Promise<LucaGuideCampaignAnalysis[]> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignAnalysis[]>(
        `/api/v2/campaigns/${campaignId}/analysis`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async get(
    campaignId: string,
    analysisId: string,
  ): Promise<LucaGuideCampaignAnalysis> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignAnalysis>(
        `/api/v2/campaigns/${campaignId}/analysis/${analysisId}`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },
};
