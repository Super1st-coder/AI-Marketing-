import { handleCommonErrors } from "../common-errors";
import { $lucaGuideApi } from "@/utils/api";

export type LucaGuideKpiFormatType =
  | "currency"
  | "percent"
  | "multiplier"
  | "ratio"
  | "count"
  | "ranking"
  | "seconds";

export type LucaGuideKpiDirection = "higher_is_better" | "lower_is_better";

export type LucaGuideKpiGroup = "primary" | "extended";

export type LucaGuideKpiCompatibility = "ideal" | "compatible" | "warning";

export type LucaGuideKpi = {
  id: string;
  key: string;
  name: string;
  format_type: LucaGuideKpiFormatType;
  direction: LucaGuideKpiDirection;
  group: LucaGuideKpiGroup;
  stage?: string | null;
  video_only: boolean;
  description: string | null;
  compatibility?: LucaGuideKpiCompatibility | string | null;
  warning?: string | null;
  has_data?: boolean | null;
};

export default {
  async list(): Promise<LucaGuideKpi[]> {
    try {
      return await $lucaGuideApi<LucaGuideKpi[]>("/api/v2/kpis", {
        method: "GET",
      });
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },
};
