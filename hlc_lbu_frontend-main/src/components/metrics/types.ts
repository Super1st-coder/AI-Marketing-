import { MetricGroup } from "@/services/UtilsApi";

export type MetricsItem = {
  name?: string | null;
  display_name?: string | null;
  unit?: string | null;
  value?: string | number | null;
  target?: string | null;
};

export type MetricsChannelGroup = {
  name: string;
  groups: Record<MetricGroup, MetricsItem[]>;
};
