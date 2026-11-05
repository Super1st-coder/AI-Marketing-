export type ClassificationThresholdKey =
  "winner" | "scalable" | "promising" | "losing";

export type ClassificationThresholdConfig = {
  key: ClassificationThresholdKey;
  color: "success" | "info" | "warning" | "error";
  icon: string;
  iconVariant: "success" | "info" | "warning" | "error";
  kpiOperator: "lte" | "gt";
};

export const CLASSIFICATION_THRESHOLDS: ClassificationThresholdConfig[] = [
  {
    key: "winner",
    color: "success",
    icon: "tabler:trophy",
    iconVariant: "success",
    kpiOperator: "lte",
  },
  {
    key: "scalable",
    color: "info",
    icon: "tabler:trending-up",
    iconVariant: "info",
    kpiOperator: "lte",
  },
  {
    key: "promising",
    color: "warning",
    icon: "tabler:clock",
    iconVariant: "warning",
    kpiOperator: "lte",
  },
  {
    key: "losing",
    color: "error",
    icon: "tabler:trending-down",
    iconVariant: "error",
    kpiOperator: "gt",
  },
];
