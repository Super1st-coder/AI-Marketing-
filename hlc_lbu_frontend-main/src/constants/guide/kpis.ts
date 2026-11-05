import type { LucaGuideKpiFormatType } from "@/services/guide/LucaGuideKpisApi";

export type KpiUnit = {
  leftIcon?: string;
  rightIcon?: string;
};

const LUCA_GUIDE_KPI_STAGES: readonly string[] = [
  "awareness",
  "traffic",
  "engagement",
  "video",
  "leads",
  "messaging",
  "conversions",
  "app",
  "landing",
  "cost",
  "diagnostics",
];

const OTHER_KPI_STAGE = "other";

export function getLucaGuideKpiStageGroup(
  stage: string | null | undefined,
): string {
  if (!stage || !LUCA_GUIDE_KPI_STAGES.includes(stage)) {
    return OTHER_KPI_STAGE;
  }

  return stage;
}

export function getLucaGuideKpiStageRank(
  stage: string | null | undefined,
): number {
  const group = getLucaGuideKpiStageGroup(stage);
  if (group === OTHER_KPI_STAGE) {
    return LUCA_GUIDE_KPI_STAGES.length;
  }

  return LUCA_GUIDE_KPI_STAGES.indexOf(group);
}

export function getLucaGuideKpiStageLabel(
  stage: string | null | undefined,
  t: (key: string) => string,
): string {
  return t(`luca-guide.kpi-stages.${getLucaGuideKpiStageGroup(stage)}`);
}

const KPI_UNITS_BY_FORMAT: Record<LucaGuideKpiFormatType, KpiUnit> = {
  currency: { leftIcon: "tabler:currency-dollar" },
  percent: { rightIcon: "tabler:percentage" },
  multiplier: { leftIcon: "tabler:x" },
  ratio: {},
  count: {},
  ranking: {},
  seconds: {},
};

export function getKpiUnitFromFormatType(
  formatType: LucaGuideKpiFormatType | null | undefined,
): KpiUnit | undefined {
  if (!formatType) {
    return undefined;
  }

  return KPI_UNITS_BY_FORMAT[formatType];
}
