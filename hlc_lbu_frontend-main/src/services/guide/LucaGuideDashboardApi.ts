import { handleCommonErrors } from "../common-errors";
import { $lucaGuideApi } from "@/utils/api";

export type LucaGuideDashboardClassification =
  "winner" | "scalable" | "promising" | "losing" | "insufficient-data";

export type LucaGuideDashboardRow = {
  campaign_id: string | null;
  name: string;
  platform: string;
  kpi_key: string;
  current_value: string;
  target_value: string;
  deviation_pct: string;
  classification: LucaGuideDashboardClassification;
  recommendation: string;
};

export type LucaGuideDashboardCategorySummary = {
  category: string;
  asset_count: number;
  total_spend: string;
};

export type LucaGuideDashboardResponse = {
  rows: LucaGuideDashboardRow[];
  requires_attention: LucaGuideDashboardRow[];
  opportunity: LucaGuideDashboardRow[];
  category_summary: LucaGuideDashboardCategorySummary[];
};

export type LucaGuideRecentActivityItem = {
  type: string;
  icon: string;
  title: string;
  subtitle: string;
  at: string;
};

export default {
  async get(): Promise<LucaGuideDashboardResponse> {
    try {
      return await $lucaGuideApi<LucaGuideDashboardResponse>(
        "/api/v2/dashboard",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getRecentActivity(limit = 8): Promise<LucaGuideRecentActivityItem[]> {
    try {
      return await $lucaGuideApi<LucaGuideRecentActivityItem[]>(
        "/api/v2/dashboard/recent-activity",
        {
          method: "GET",
          query: { limit },
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },
};
