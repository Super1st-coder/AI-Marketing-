import { CampaignData } from "@/services/projects/CampaignsApi";
import { MetricGroup } from "@/services/UtilsApi";

/**
 * Builds a human-readable summary of the structured metrics saved in the
 * "KPIs" wizard step (step 4) for a given metric group.
 *
 * The campaign Summary step normally shows the AI-generated text stored in
 * `summary_saved` / `summary_generated` (`campaign_goals`, `campaign_resources`,
 * `campaign_kpis`). When that generated text is missing/empty for a group
 * (notably the "Marketing" / Performance KPIs group — see HL-2684), we fall
 * back to the actual saved metrics so the values the user entered still render,
 * matching how Goals and Resources behave.
 *
 * Returns an empty string when there are no saved metrics for the group, so it
 * can be chained with `||` fallbacks.
 */
export function buildMetricsSummaryText(
  campaign: Pick<CampaignData, "channel_group">,
  group: MetricGroup,
): string {
  const metrics = (campaign.channel_group ?? []).flatMap(
    (channelGroup) => channelGroup?.metrics ?? [],
  );

  const lines = metrics
    .filter((metric) => metric && metric.group === group)
    .map((metric) => {
      const label = (metric.display_name || metric.name || "").trim();
      if (!label) return "";

      const rawValue =
        metric.value != null && String(metric.value).trim() !== ""
          ? String(metric.value).trim()
          : metric.target != null && String(metric.target).trim() !== ""
            ? String(metric.target).trim()
            : "";

      const unit = metric.unit ? ` ${metric.unit}` : "";

      return rawValue ? `${label}: ${rawValue}${unit}` : label;
    })
    .filter((line) => line !== "");

  // De-duplicate while preserving order (metrics can repeat across channels).
  return [...new Set(lines)].join("\n");
}
