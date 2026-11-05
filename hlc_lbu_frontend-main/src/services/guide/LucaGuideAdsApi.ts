import { handleCommonErrors } from "../common-errors";
import { $lucaGuideApi } from "@/utils/api";
import { getFilenameFromContentDisposition } from "@/utils/download";
import type { LucaGuideDashboardClassification } from "@/services/guide/LucaGuideDashboardApi";
import type { LucaGuideNorthStarPriority } from "@/services/guide/LucaGuideOnboardingApi";
import type { LucaGuideKpiFormatType } from "@/services/guide/LucaGuideKpisApi";

export type LucaGuideAdTrend = "rise" | "fall" | "stable" | "new";

export type LucaGuideAd = {
  ad_external_id: string;
  campaign_external_id: string;
  ad_name: string;
  asset_type: string;
  state: LucaGuideDashboardClassification;
  primary_kpi: string;
  primary_kpi_value: number;
  primary_kpi_target: number;
  ctr: number;
  cpm: number;
  cvr: number;
  total_impressions: number;
  total_conversions: number;
  total_spend: number;
  cta: string | null;
  headline: string | null;
  image_url: string | null;
};

export type LucaGuideAdPerformanceSummaryKpi = {
  priority: LucaGuideNorthStarPriority;
  key: string;
  name: string;
  format: LucaGuideKpiFormatType;
  value: number;
  windowed_value: number;
  target: number;
  good: boolean;
  windowed_good: boolean;
  lower_better: boolean;
  series: number[];
};

export type LucaGuideAdPerformanceSummary = {
  ad_external_id: string;
  ad_name: string;
  state: LucaGuideDashboardClassification;
  windowed_state: LucaGuideDashboardClassification;
  has_data: boolean;
  trend: LucaGuideAdTrend;
  explanation: string | null;
  timeframe_days: number;
  timeframe_label: string;
  window_start: string;
  window_end: string;
  window_days: number;
  window_label: string;
  daily_available: boolean;
  auto_ranged: boolean;
  kpis: LucaGuideAdPerformanceSummaryKpi[];
};

export type LucaGuidePerformanceSummaryQuery = {
  days?: number;
  autoRange?: boolean;
  startDate?: string;
  endDate?: string;
};

export type LucaGuideAdContent = {
  ad_external_id: string;
  asset_type: string;
  headline: string | null;
  primary_text: string | null;
  cta: string | null;
  description: string | null;
};

export type LucaGuideAdVideoSource = {
  ok: boolean;
  reason?: string;
  video_id?: string;
  error?: string;
  source_url?: string;
  embed_url?: string;
  permalink_url?: string;
};

export type LucaGuideAdPreviewIframe = {
  ok: boolean;
  ad_format?: string;
  iframe?: string;
};

export type LucaGuideParsedIframe = {
  src: string;
  width?: number;
  height?: number;
  allow?: string;
};

export function parseIframeFromHtml(
  html: string,
): LucaGuideParsedIframe | undefined {
  const srcMatch = html.match(/\ssrc=["']([^"']+)["']/i);

  if (!srcMatch?.[1]) {
    return undefined;
  }

  const width = Number(html.match(/\swidth=["'](\d+)["']/i)?.[1]);
  const height = Number(html.match(/\sheight=["'](\d+)["']/i)?.[1]);
  const allow = html.match(/\sallow=["']([^"']+)["']/i)?.[1];

  return {
    src: srcMatch[1].replaceAll("&amp;", "&"),
    width: Number.isFinite(width) && width > 0 ? width : undefined,
    height: Number.isFinite(height) && height > 0 ? height : undefined,
    allow: allow || undefined,
  };
}

export type LucaGuideAdDiagnosisHealth = "healthy" | "watch" | "warning";

export type LucaGuideAdDiagnosisConfidence = "low" | "medium" | "high";

export type LucaGuideAdDiagnosisKpiStatus = "good" | "bad" | "neutral";

export type LucaGuideAdDiagnosisKpi = {
  label: string;
  value: string;
  benchmark: string | null;
  status: LucaGuideAdDiagnosisKpiStatus;
};

export type LucaGuideAdDiagnosisSlot = {
  slot: string;
  slot_index: number;
  title: string;
  icon_name: string;
  health: LucaGuideAdDiagnosisHealth;
  score: number;
  headline: string;
  kpis: LucaGuideAdDiagnosisKpi[];
  recommendation: string;
  recommendation_tag: string;
  persona_angle: string | null;
  brief_seeds: string[] | null;
  confidence: LucaGuideAdDiagnosisConfidence;
  rationale: string;
};

export type LucaGuideAdDiagnosis = {
  ad_external_id: string;
  campaign_external_id: string;
  generated_at: string;
  lucas_spent: number;
  asset_type: string;
  cards: LucaGuideAdDiagnosisSlot[];
};

export type LucaGuideAdInsightsStatusSlot = {
  slot: string;
  slot_index: number;
  title: string;
  status: "processing" | "pending" | "completed";
  generated_by: string;
};

export type LucaGuideAdInsightsStatus = {
  ad_external_id: string;
  slots: LucaGuideAdInsightsStatusSlot[];
  completed: number;
  total: number;
  all_completed: boolean;
};

export type LucaGuideAdInsightEvidenceKpi = {
  label: string;
  value: string;
  benchmark: string;
};

export type LucaGuideAdInsightDiagnosis = {
  brief_title: string;
  diagnosis: string;
  evidence: string;
  evidence_kpis: LucaGuideAdInsightEvidenceKpi[];
  creative_correlation: string;
};

export type LucaGuideAdInsightHypothesis = {
  if_clause: string;
  then_clause: string;
  locked_output: string;
};

export type LucaGuideAdInsightContext = {
  objective: string;
  hypothesis: LucaGuideAdInsightHypothesis;
  target_kpi: string;
  min: number;
  max: number;
  cause_and_effect: string;
};

export type LucaGuideAdInsightActions = {
  brief_ready: string;
  risk_of_not_acting: string;
  recommended_actions: string[];
  success_criteria: string[];
  persona_angle: string;
};

export type LucaGuideAdInsightChangeMethod = {
  value: string;
  label: string;
};

export type LucaGuideAdInsight = {
  slot: string;
  slot_index: number;
  title: string;
  persona: string | null;
  ad_diagnosis: LucaGuideAdInsightDiagnosis;
  context: LucaGuideAdInsightContext;
  actions: LucaGuideAdInsightActions;
  generated_by: string;
  cached?: boolean;
  status?: string;
  change_methods?: LucaGuideAdInsightChangeMethod[];
};

export type LucaGuideAdInsightPdfPayload = Pick<
  LucaGuideAdInsight,
  "slot" | "slot_index" | "title" | "ad_diagnosis" | "context" | "actions"
>;

export type LucaGuideHypothesisSynthesizeRequest = {
  if_condition: string;
  then_condition: string;
  kpi_name: string;
  min_pct: number;
  max_pct: number;
};

export type LucaGuideHypothesisSynthesizeResponse = {
  synthesized_hypothesis: string;
};

export const LUCA_GUIDE_HYPOTHESIS_METHODS = [
  "AB_ISOLATION",
  "ESCALATING_GROUP",
  "CREATIVE_VARIANTS",
] as const;

export type LucaGuideHypothesisMethod =
  (typeof LUCA_GUIDE_HYPOTHESIS_METHODS)[number];

export type LucaGuideHypothesisRecommendMethodRequest = {
  ad_external_id: string;
  slot_index: number;
  synthesized_hypothesis: string;
};

export type LucaGuideHypothesisRecommendMethodResponse = {
  ai_recommended_method: LucaGuideHypothesisMethod;
  reason: string;
  source: string;
};

export type LucaGuideAdInsightsStart = {
  ad_external_id: string;
  selected_slot: string;
  selected_slot_index: number;
  selection_reason: string;
  recommended_next_move: LucaGuideAdInsight;
  background: {
    remaining: number;
    note: string;
  };
  slots: LucaGuideAdInsightsStatusSlot[];
};

export type LucaGuideAdRecommendedNextMovePriorityFactors = {
  impact: number;
  confidence: number;
  urgency: number;
  action_risk: number;
};

export type LucaGuideAdRecommendedNextMovePriority = {
  score: number;
  bucket: string;
  factors: LucaGuideAdRecommendedNextMovePriorityFactors;
  formula: string;
};

export type LucaGuideAdRecommendedNextMoveDecision = {
  diagnosis: string;
  interpretation: string;
  recommended_action: string;
  risk_of_not_acting: string;
  success_criteria: string;
  suggested_action_label: string;
  secondary_lever: string | null;
};

export type LucaGuideAdRecommendedNextMoveRankingItem = {
  lever: string;
  slot: string;
  priority_score: number;
  priority: string;
  passive: boolean;
  action_type: string;
};

export type LucaGuideAdRecommendedNextMove = {
  ad_external_id: string;
  selected_slot: string;
  selected_slot_index: number;
  lever: string;
  action_type: string;
  priority: LucaGuideAdRecommendedNextMovePriority;
  selection_reason: string;
  decision: LucaGuideAdRecommendedNextMoveDecision;
  recommended_next_move: LucaGuideAdInsight;
  ranking: LucaGuideAdRecommendedNextMoveRankingItem[];
  engine: string;
};

export type LucaGuideAdDataDeliveryEvidence = {
  label: string;
  value: string | number;
  reference_label?: string | null;
  reference?: string | number | null;
};

export type LucaGuideAdDataDeliveryRecommendation = {
  rule_id: string;
  version: string;
  lever: string;
  family: string;
  title: string;
  severity: string;
  diagnosis: string;
  interpretation: string;
  recommendation: string;
  risk_of_not_acting: string;
  success_criteria: string;
  evidence: LucaGuideAdDataDeliveryEvidence[];
  action_type: string;
  action_type_label: string;
  action_color: string;
  calibration_warning: string | null;
  allow_direct_action: boolean;
  card_key: string;
  card_id: string;
  rule_version: string;
  confidence?: number;
};

export type LucaGuideAdDataDeliveryInboxEvidence = {
  diagnosisSlot: string | null;
  cardTitle: string;
  detail: string;
};

export type LucaGuideAdDataDeliveryInboxItem = {
  itemId: string;
  campaignId: string;
  adId: string;
  adName: string;
  adSetId: string | null;
  adSetName: string | null;
  scope: string;
  classification: string;
  lever: string;
  macroGroup: string;
  actionType: string;
  passive: boolean;
  priority: string;
  priorityScore: number;
  diagnosis: string;
  evidence: LucaGuideAdDataDeliveryInboxEvidence[];
  interpretation: string;
  riskOfNotActing: string;
  recommendedAction: string;
  successCriteria: string;
  suggestedActionLabel: string;
  calibrationWarning: string | null;
  allowDirectAction: boolean;
  actionColor: string;
};

export type LucaGuideAdDataDeliveryEvaluationSummary = {
  fired: number;
  not_fired: number;
  missing_data: number;
  insufficient_data: number;
  not_applicable: number;
};

export type LucaGuideAdDataDelivery = {
  enabled: boolean;
  ad_external_id: string;
  data_recommendations?: LucaGuideAdDataDeliveryRecommendation[];
  delivery_recommendations?: LucaGuideAdDataDeliveryRecommendation[];
  inbox_items?: LucaGuideAdDataDeliveryInboxItem[];
  evaluation_summary?: LucaGuideAdDataDeliveryEvaluationSummary;
};

export default {
  async list(): Promise<LucaGuideAd[]> {
    try {
      return await $lucaGuideApi<LucaGuideAd[]>("/api/v2/ads", {
        method: "GET",
      });
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getPerformanceSummary(
    adExternalId: string,
    query: LucaGuidePerformanceSummaryQuery = {},
  ): Promise<LucaGuideAdPerformanceSummary> {
    try {
      const { startDate, endDate, days = 7, autoRange = false } = query;
      const hasDateRange = Boolean(startDate && endDate);

      return await $lucaGuideApi<LucaGuideAdPerformanceSummary>(
        `/api/v2/ads/${adExternalId}/performance-summary`,
        {
          method: "GET",
          query: hasDateRange
            ? { start_date: startDate, end_date: endDate }
            : {
                days,
                auto_range: autoRange ? 1 : undefined,
              },
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getContent(adExternalId: string): Promise<LucaGuideAdContent> {
    try {
      return await $lucaGuideApi<LucaGuideAdContent>(
        `/api/v2/ads/${adExternalId}/content`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getVideoSource(adExternalId: string): Promise<LucaGuideAdVideoSource> {
    try {
      return await $lucaGuideApi<LucaGuideAdVideoSource>(
        `/api/v2/ads/${adExternalId}/video-source`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getPreview(adExternalId: string): Promise<LucaGuideAdPreviewIframe> {
    try {
      return await $lucaGuideApi<LucaGuideAdPreviewIframe>(
        `/api/v2/ads/${adExternalId}/preview`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  // Ticket 18: the stored Meta image_url is a signed scontent-*.fbcdn.net link that expires (403 →
  // broken preview). Fetch the creative image through our proxy (fresh from Meta, streamed from our
  // own domain, so it never expires in the browser and ad-blockers can't hide it) as a blob via the
  // authenticated client, and hand back an object URL for <img src>. null → caller keeps its fallback.
  async getCreativeImageUrl(adExternalId: string): Promise<string | null> {
    try {
      const response = await $lucaGuideApi.raw(
        `/api/v2/ads/${adExternalId}/creative-image`,
        { method: "GET", responseType: "blob" },
      );
      const blob = response._data as Blob | undefined;
      if (!blob || blob.size === 0) {
        return null;
      }
      return URL.createObjectURL(blob);
    } catch {
      // 404/no-image, expired, or network → let the caller fall back to the stored image_url.
      return null;
    }
  },

  async generateDiagnosis(
    adExternalId: string,
    window?: { days?: number; startDate?: string; endDate?: string },
  ): Promise<LucaGuideAdDiagnosis> {
    try {
      // Pass the selected date window so the analysis reflects it (Marco): a custom range wins,
      // else the preset days; omitted → lifetime-aggregate (backward-compatible).
      const query =
        window?.startDate && window?.endDate
          ? { start_date: window.startDate, end_date: window.endDate }
          : window?.days != null
            ? { days: window.days }
            : undefined;
      return await $lucaGuideApi<LucaGuideAdDiagnosis>(
        `/api/v2/ads/${adExternalId}/diagnosis`,
        {
          method: "POST",
          query,
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  // HLG-181: fetch the latest SAVED diagnosis for an ad (GET), so a generated diagnosis persists
  // across page reloads instead of asking the user to generate (and pay) again. Returns null when
  // none exists yet (404) or on any read failure, so the ad-detail page falls back to the empty-
  // state "Generate" card rather than breaking on load.
  async getDiagnosis(
    adExternalId: string,
  ): Promise<LucaGuideAdDiagnosis | null> {
    try {
      return await $lucaGuideApi<LucaGuideAdDiagnosis>(
        `/api/v2/ads/${adExternalId}/diagnosis`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      // 404 = no diagnosis generated yet (expected). Any other status → don't break the page
      // load; the user can (re)generate. Log non-404s for visibility.
      const status =
        (error as any)?.statusCode ?? (error as any)?.response?.status;
      if (status !== 404) {
        console.error("Failed to load saved diagnosis:", error);
      }
      return null;
    }
  },

  async startInsights(adExternalId: string): Promise<LucaGuideAdInsightsStart> {
    try {
      return await $lucaGuideApi<LucaGuideAdInsightsStart>(
        `/api/v2/ads/${adExternalId}/insights/start`,
        {
          method: "POST",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getInsightsStatus(
    adExternalId: string,
  ): Promise<LucaGuideAdInsightsStatus> {
    try {
      return await $lucaGuideApi<LucaGuideAdInsightsStatus>(
        `/api/v2/ads/${adExternalId}/insights/status`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getSlotInsight(
    adExternalId: string,
    slotIndex: number,
    window?: { startDate?: string; endDate?: string },
  ): Promise<LucaGuideAdInsight> {
    try {
      // Pass the selected window so the slot insight's performance stays consistent with the
      // Performance Summary + the windowed diagnosis (Marco).
      const query =
        window?.startDate && window?.endDate
          ? { start_date: window.startDate, end_date: window.endDate }
          : undefined;
      return await $lucaGuideApi<LucaGuideAdInsight>(
        `/api/v2/ads/${adExternalId}/slot-insight/${slotIndex}`,
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

  async getDataDelivery(
    adExternalId: string,
  ): Promise<LucaGuideAdDataDelivery> {
    try {
      return await $lucaGuideApi<LucaGuideAdDataDelivery>(
        `/api/v2/ads/${adExternalId}/data-delivery`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getRecommendedNextMove(
    adExternalId: string,
  ): Promise<LucaGuideAdRecommendedNextMove> {
    try {
      return await $lucaGuideApi<LucaGuideAdRecommendedNextMove>(
        `/api/v2/ads/${adExternalId}/recommended-next-move`,
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async exportSlotInsightPdf(
    adExternalId: string,
    slotIndex: number,
    body: LucaGuideAdInsightPdfPayload,
  ): Promise<{ blob: Blob; filename: string }> {
    try {
      const response = await $lucaGuideApi.raw(
        `/api/v2/ads/${adExternalId}/slot-insight/${slotIndex}/pdf`,
        {
          method: "POST",
          body,
          responseType: "blob",
        },
      );

      const blob = response._data;
      if (!blob) {
        throw new Error("Empty PDF response");
      }

      const filename =
        getFilenameFromContentDisposition(
          response.headers.get("content-disposition"),
        ) ?? `slot-insight-${slotIndex}.pdf`;

      return { blob, filename };
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async synthesizeHypothesis(
    body: LucaGuideHypothesisSynthesizeRequest,
  ): Promise<LucaGuideHypothesisSynthesizeResponse> {
    try {
      return await $lucaGuideApi<LucaGuideHypothesisSynthesizeResponse>(
        "/api/v2/hypothesis/synthesize",
        {
          method: "POST",
          body,
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async recommendHypothesisMethod(
    body: LucaGuideHypothesisRecommendMethodRequest,
  ): Promise<LucaGuideHypothesisRecommendMethodResponse> {
    try {
      return await $lucaGuideApi<LucaGuideHypothesisRecommendMethodResponse>(
        "/api/v2/hypothesis/recommend-method",
        {
          method: "POST",
          body,
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },
};
