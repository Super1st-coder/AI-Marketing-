import { handleCommonErrors } from "../common-errors";
import { $lucaGuideApi } from "@/utils/api";

export type LucaGuideOnboardingState = {
  has_completed: boolean;
  show_tutorial: boolean;
};

export type LucaGuideMetaConnection = {
  status: "connected" | "disconnected";
  selected_ad_account_id: string | null;
  selected_business_page_id: string | null;
  currency: string | null;
  /**
   * HLG-171: the persisted "Historical period" selection, so the selector can
   * rehydrate after save. `historical_period_days` is the saved window in days
   * (1095 === "Entire period", see {@link LUCA_GUIDE_ENTIRE_PERIOD_DAYS}); when
   * a custom range was chosen, `historical_period_start`/`_end` hold its bounds.
   */
  historical_period_days: number | null;
  historical_period_start: string | null;
  historical_period_end: string | null;
};

export type LucaGuideDataSyncStatus = {
  syncing: boolean;
  state: string | null;
  available_days: number;
  first_date: string | null;
  last_date: string | null;
  // Download progress for the UI bar + ETA. `pct` is 0–100 (from Meta's async job); `started_at`
  // is the sync start (ISO) so the client can estimate time-left. Both null before the first sync.
  pct: number | null;
  started_at: string | null;
};

export type LucaGuideMetaAdAccount = {
  id: string;
  name: string | null;
  currency: string | null;
  account_status: number | null;
  amount_spent: string | null;
};

export type LucaGuidePrepareMetaAccountDateFilter =
  { days: number } | { date_start: string; date_end: string };

export type LucaGuidePrepareMetaAccountResponse = {
  account_id?: string;
  ingested_rows?: number;
  classified_ads?: number;
  note?: string;
  window_label?: string;
  message?: string;
};

// Async prepare-account job: the ingest is too slow to run in one HTTP request on a real account,
// so the wizard kicks a job (start) and polls its state (status) until it's terminal.
export type LucaGuidePrepareJobState =
  "none" | "running" | "done" | "empty" | "failed";

export type LucaGuidePrepareJobStatus = {
  job_id?: string;
  state: LucaGuidePrepareJobState;
  account_id?: string;
  classified_ads?: number | null;
  ingested_rows?: number | null;
  note?: string | null;
  message?: string | null;
  error?: string | null;
  window_label?: string;
  window?: { days?: number | null; start?: string | null; end?: string | null };
};

export const LUCA_GUIDE_NORTH_STAR_PRIORITIES = [
  "primary",
  "secondary",
  "tertiary",
] as const;

export type LucaGuideNorthStarPriority =
  (typeof LUCA_GUIDE_NORTH_STAR_PRIORITIES)[number];

export type LucaGuideNorthStarItem = {
  priority: LucaGuideNorthStarPriority;
  kpi_id: string;
  target_value: string;
};

export type LucaGuideNorthStarItemInput = {
  priority: LucaGuideNorthStarPriority;
  kpi_id: string;
  target_value: number | string;
};

export type LucaGuideNorthStarSaveResponse = {
  items: LucaGuideNorthStarItem[];
  warnings: string[];
};

export type LucaGuideThresholdCategory =
  "winner" | "scalable" | "promising" | "losing";

export type LucaGuideThresholdItem = {
  category: LucaGuideThresholdCategory;
  min_impressions: number;
  use_conversions: boolean;
  min_conversions: number;
  min_days_running: number;
  kpi_band_pct: string;
};

export type LucaGuideThresholdItemInput = {
  category: LucaGuideThresholdCategory;
  min_impressions: number;
  use_conversions: boolean;
  min_conversions: number;
  min_days_running: number;
  kpi_band_pct: number | string;
};

export default {
  async getState(): Promise<LucaGuideOnboardingState> {
    try {
      return await $lucaGuideApi<LucaGuideOnboardingState>(
        "/api/v2/onboarding",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async updateTutorial(
    showTutorial: boolean,
  ): Promise<LucaGuideOnboardingState> {
    try {
      return await $lucaGuideApi<LucaGuideOnboardingState>(
        "/api/v2/onboarding/tutorial",
        {
          method: "PATCH",
          body: {
            show_tutorial: showTutorial,
          },
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getMeta(): Promise<LucaGuideMetaConnection> {
    try {
      return await $lucaGuideApi<LucaGuideMetaConnection>(
        "/api/v2/onboarding/meta",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  // Daily-metric sync progress: is the post-connect backfill still running, and how many
  // distinct days are loaded so far. The Overview page uses this to show a "syncing" banner
  // and to gate the window buttons to what's actually loaded (Jake).
  async getSyncStatus(): Promise<LucaGuideDataSyncStatus> {
    try {
      return await $lucaGuideApi<LucaGuideDataSyncStatus>(
        "/api/v2/onboarding/meta/sync-status",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  // Re-run the daily backfill (owner/admin) without disconnecting — refreshes/repairs the data and
  // lets the user watch the download progress bar. Idempotent; returns immediately.
  async triggerDataSync(): Promise<{ started: boolean }> {
    try {
      return await $lucaGuideApi<{ started: boolean }>(
        "/api/v2/ingestion/backfill",
        {
          method: "POST",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async listMetaAdAccounts(): Promise<LucaGuideMetaAdAccount[]> {
    try {
      return await $lucaGuideApi<LucaGuideMetaAdAccount[]>(
        "/api/v2/onboarding/meta/ad-accounts",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async prepareMetaAccount(
    accountId: string,
    dateFilter?: LucaGuidePrepareMetaAccountDateFilter,
  ): Promise<LucaGuidePrepareMetaAccountResponse> {
    try {
      return await $lucaGuideApi<LucaGuidePrepareMetaAccountResponse>(
        "/api/v2/onboarding/meta/prepare-account",
        {
          method: "POST",
          params: {
            account_id: accountId,
            ...dateFilter,
          },
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  // Kick the async ingest — returns immediately with a `running` job. Poll getPrepareStatus.
  async startPrepareMetaAccount(
    accountId: string,
    dateFilter?: LucaGuidePrepareMetaAccountDateFilter,
  ): Promise<LucaGuidePrepareJobStatus> {
    try {
      return await $lucaGuideApi<LucaGuidePrepareJobStatus>(
        "/api/v2/onboarding/meta/prepare-account/start",
        {
          method: "POST",
          params: {
            account_id: accountId,
            ...dateFilter,
          },
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getPrepareStatus(): Promise<LucaGuidePrepareJobStatus> {
    try {
      return await $lucaGuideApi<LucaGuidePrepareJobStatus>(
        "/api/v2/onboarding/meta/prepare-account/status",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async disconnect(): Promise<LucaGuideOnboardingState> {
    try {
      return await $lucaGuideApi<LucaGuideOnboardingState>(
        "/api/v2/onboarding/disconnect",
        {
          method: "POST",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getNorthStar(): Promise<LucaGuideNorthStarItem[]> {
    try {
      return await $lucaGuideApi<LucaGuideNorthStarItem[]>(
        "/api/v2/onboarding/north-star",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async setNorthStar(
    items: LucaGuideNorthStarItemInput[],
  ): Promise<LucaGuideNorthStarSaveResponse> {
    try {
      return await $lucaGuideApi<LucaGuideNorthStarSaveResponse>(
        "/api/v2/onboarding/north-star",
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

  async getThresholds(): Promise<LucaGuideThresholdItem[]> {
    try {
      return await $lucaGuideApi<LucaGuideThresholdItem[]>(
        "/api/v2/onboarding/thresholds",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getThresholdDefaults(): Promise<LucaGuideThresholdItem[]> {
    try {
      return await $lucaGuideApi<LucaGuideThresholdItem[]>(
        "/api/v2/onboarding/thresholds/defaults",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async setThresholds(
    items: LucaGuideThresholdItemInput[],
  ): Promise<LucaGuideThresholdItem[]> {
    try {
      return await $lucaGuideApi<LucaGuideThresholdItem[]>(
        "/api/v2/onboarding/thresholds",
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

  async complete(): Promise<LucaGuideOnboardingState> {
    try {
      return await $lucaGuideApi<LucaGuideOnboardingState>(
        "/api/v2/onboarding/complete",
        {
          method: "POST",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },
};
