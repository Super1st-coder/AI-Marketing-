import { handleCommonErrors } from "../common-errors";
import { $lucaGuideApi } from "@/utils/api";
import type {
  LucaGuideKpi,
  LucaGuideKpiFormatType,
} from "@/services/guide/LucaGuideKpisApi";
import type { LucaGuideNorthStarPriority } from "@/services/guide/LucaGuideOnboardingApi";
import type { LucaGuideAdTrend } from "@/services/guide/LucaGuideAdsApi";

export type LucaGuideCampaignStateCounts = {
  winner: number;
  scalable: number;
  promising: number;
  losing: number;
};

export type LucaGuideCampaignHealth =
  "pending" | "on_track" | "alert" | "watch";

export type LucaGuideCampaign = {
  campaign_id: string;
  external_id: string;
  name: string;
  objective: string;
  optimization_goal: string | null;
  result_type: string | null;
  status: "active";
  ad_count: number;
  state_counts: LucaGuideCampaignStateCounts;
  has_primary_kpi: boolean;
  total_spend: number;
  health: LucaGuideCampaignHealth;
  objective_label: string;
  context_status: "without" | "partial" | "with";
};

export type LucaGuideCampaignContextStatus =
  "FULL_CONTEXT" | "PARTIAL_CONTEXT" | "NO_CONTEXT";

export type LucaGuideCampaignContext = {
  campaign_id: string;
  context_status: LucaGuideCampaignContextStatus;
  analysis_enabled: boolean;
  generation_enabled: boolean;
  product_id: string | null;
  persona_id: string | null;
  project_id: string | null;
  umbrella_campaign_id: string | null;
  /** HLG-120: the 5th element — the linked Builder Campaign. */
  linked_campaign_id: string | null;
  audience_id: string | null;
  linked_count: number;
  missing_links: string[];
  show_context_warning: boolean;
  /** HLG-120: 0–5 across all five context elements (drives the "X of 5" ring). */
  linked_elements_count: number;
  /** HLG-120: true only at 5/5 (four assets + a linked campaign). */
  has_builder_context: boolean;
  /** HLG-120: BUILDER_NATIVE | MANUAL_LINKED | NONE. */
  context_source: "BUILDER_NATIVE" | "MANUAL_LINKED" | "NONE";
  /**
   * True when the campaign was synced from Builder.
   * False / missing = Meta-imported.
   */
  created_from_builder?: boolean;
};

// HLG-120: the channel-group brief on the metrics step — Goals / Resources / Performance KPIs,
// resolved from the campaign's linked Builder campaign.
export type LucaGuideCampaignBriefMetric = {
  label: string | null;
  value: string | null;
  target: string | null;
  unit: string | null;
};

export type LucaGuideCampaignBriefGroup = {
  name: string | null;
  type: string | null;
  description: string | null;
  goals: LucaGuideCampaignBriefMetric[];
  resources: LucaGuideCampaignBriefMetric[];
  performance_kpis: LucaGuideCampaignBriefMetric[];
};

export type LucaGuideCampaignBrief = {
  has_brief: boolean;
  channel_groups: LucaGuideCampaignBriefGroup[];
  big_idea?: string | null;
  timing?: string | null;
};

export type LucaGuideCampaignContextUpdate = {
  product_id?: string | null;
  persona_id?: string | null;
  project_id?: string | null;
  umbrella_campaign_id?: string | null;
  /** HLG-120: the linked Builder Campaign (5th element). */
  linked_campaign_id?: string | null;
};

export type LucaGuideCampaignHomeSummary = {
  active_campaigns: number;
  pending_setup: number;
  opportunity: number;
  requires_attention: number;
};

export type LucaGuideOverviewKpiMetric = {
  key: string;
  name: string;
  format: LucaGuideKpiFormatType;
  value: number | null;
  target: number | null;
  good: boolean | null;
  lower_better: boolean;
};

export type LucaGuideOverviewNorthStarMetric = LucaGuideOverviewKpiMetric & {
  priority: LucaGuideNorthStarPriority;
};

export type LucaGuideOverviewSpendBucket = {
  ads: number;
  spend: number;
  pct_spend: number;
};

export type LucaGuideOverviewCampaign = Pick<
  LucaGuideCampaign,
  | "campaign_id"
  | "external_id"
  | "name"
  | "objective"
  | "has_primary_kpi"
  | "context_status"
> & {
  status: LucaGuideCampaignHealth;
  primary: LucaGuideOverviewKpiMetric | null;
  spend: number;
  ads: number;
};

export type LucaGuideCampaignsOverview = {
  currency: string;
  timeframe_days: number | null;
  account_north_star: LucaGuideOverviewNorthStarMetric[];
  totals: {
    spend: number;
    conversions: number;
    active_ads: number;
    active_campaigns: number;
    // HLG-177: total campaigns in the account (backend mirrors scope.total_campaigns here) so the
    // account North Star can label its scope "N of M campaigns" instead of implying it covers all.
    total_campaigns: number;
  };
  spend_distribution: Record<
    keyof LucaGuideCampaignStateCounts,
    LucaGuideOverviewSpendBucket
  >;
  campaigns: LucaGuideOverviewCampaign[];
};

export type LucaGuideCampaignKpiItem = {
  priority: LucaGuideNorthStarPriority | string;
  kpi_id: string;
  target_value: number | string;
};

export type LucaGuideCampaignKpiRow = Omit<
  LucaGuideCampaignKpiItem,
  "target_value"
> & {
  target_value: string;
  aligned: boolean;
  current_value?: number | null;
  has_data?: boolean;
  // Why the value is blank (when has_data is false): "objective_mismatch" (Meta doesn't report this
  // metric for the campaign's objective) or "no_data" (not enough data yet). Drives the "—" caption.
  unavailable_reason?: string | null;
};

export type LucaGuideCampaignKpisResponse = {
  items: LucaGuideCampaignKpiRow[];
  has_misaligned: boolean;
  warnings?: string[];
};

export type LucaGuideCampaignAdsTableKpi = {
  priority: LucaGuideNorthStarPriority;
  key: string;
  name: string;
  target: number;
  format: LucaGuideKpiFormatType;
  lower_better: boolean;
};

export type LucaGuideCampaignAdsTableAdValue = {
  value: number | null;
  good: boolean | null;
};

export type LucaGuideCampaignAdsTableAd = {
  ad_external_id: string;
  ad_name: string;
  ad_set_name?: string | null;
  state: string;
  values: LucaGuideCampaignAdsTableAdValue[];
  spend: number;
  trend: LucaGuideAdTrend;
  diagnosed: boolean;
};

export type LucaGuideCampaignAdsTableTotals = {
  ad_count: number;
  spend: number;
  // HLG-193: windowed impressions/conversions for the campaign-page header, so it reads the same
  // daily-span totals as the ad-set list/ads table (optional — older backends omit them).
  impressions?: number;
  conversions?: number;
  values: LucaGuideCampaignAdsTableAdValue[];
};

export type LucaGuideCampaignAdsTableAdSet = LucaGuideCampaignAdsTableTotals & {
  ad_set_name: string | null;
};

export type LucaGuideCampaignAdsTable = {
  kpis: LucaGuideCampaignAdsTableKpi[];
  ads: LucaGuideCampaignAdsTableAd[];
  ad_sets: LucaGuideCampaignAdsTableAdSet[];
  totals: LucaGuideCampaignAdsTableTotals;
};

export default {
  async list(): Promise<LucaGuideCampaign[]> {
    try {
      return await $lucaGuideApi<LucaGuideCampaign[]>("/api/v2/campaigns", {
        method: "GET",
      });
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getOverview(
    days?: number,
    startDate?: string,
    endDate?: string,
  ): Promise<LucaGuideCampaignsOverview> {
    try {
      const query =
        startDate && endDate
          ? { start_date: startDate, end_date: endDate }
          : days != null
            ? { days }
            : undefined;
      return await $lucaGuideApi<LucaGuideCampaignsOverview>(
        "/api/v2/campaigns/overview",
        {
          method: "GET",
          query,
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getHomeSummary(): Promise<LucaGuideCampaignHomeSummary> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignHomeSummary>(
        "/api/v2/campaigns/home-summary",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getBrief(campaignId: string): Promise<LucaGuideCampaignBrief> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignBrief>(
        `/api/v2/campaigns/${campaignId}/brief`,
        { method: "GET" },
      );
    } catch {
      // A brief must never break the metrics step — degrade to the empty placeholder.
      return { has_brief: false, channel_groups: [] };
    }
  },

  async getContext(
    campaignId: string,
  ): Promise<LucaGuideCampaignContext | null> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignContext>(
        `/api/v2/campaigns/${campaignId}/context`,
        {
          method: "GET",
        },
      );
    } catch {
      return null;
    }
  },

  async setContext(
    campaignId: string,
    body: LucaGuideCampaignContextUpdate,
  ): Promise<LucaGuideCampaignContext> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignContext>(
        `/api/v2/campaigns/${campaignId}/context`,
        {
          method: "PUT",
          body,
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getKpis(campaignId: string): Promise<LucaGuideCampaignKpisResponse> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignKpisResponse>(
        `/api/v2/campaigns/${campaignId}/kpis`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async setKpis(
    campaignId: string,
    items: LucaGuideCampaignKpiItem[],
  ): Promise<LucaGuideCampaignKpisResponse> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignKpisResponse>(
        `/api/v2/campaigns/${campaignId}/kpis`,
        {
          method: "PUT",
          body: { items },
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getKpiOptions(campaignId: string): Promise<LucaGuideKpi[]> {
    try {
      return await $lucaGuideApi<LucaGuideKpi[]>(
        `/api/v2/campaigns/${campaignId}/kpi-options`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getAdsTable(
    campaignId: string,
    days?: number,
  ): Promise<LucaGuideCampaignAdsTable> {
    try {
      return await $lucaGuideApi<LucaGuideCampaignAdsTable>(
        `/api/v2/campaigns/${campaignId}/ads-table`,
        {
          method: "GET",
          query: days != null ? { days } : undefined,
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },
};
