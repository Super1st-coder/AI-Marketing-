import type { LucaGuideAd } from "@/services/guide/LucaGuideAdsApi";
import type { LucaGuideKpiFormatType } from "@/services/guide/LucaGuideKpisApi";

export type LucaGuideKpiTargetTone =
  "success" | "warning" | "error" | "secondary";

const KPI_CHART_COLORS: Record<LucaGuideKpiTargetTone, string> = {
  success: "#12b76a",
  warning: "#f79009",
  error: "#f04438",
  secondary: "#808390",
};

/** ApexCharts-compatible hex colors aligned with theme tokens in main.css. */
export function getLucaGuideKpiChartColor(
  tone: LucaGuideKpiTargetTone,
): string {
  return KPI_CHART_COLORS[tone];
}

/** Max % deviation from target still treated as "close" (orange). */
export const LUCA_GUIDE_KPI_NEAR_TARGET_PERCENT = 10;

export function getLucaGuideKpiTargetTone(
  current: number | null | undefined,
  target: number,
  lowerIsBetter: boolean,
  hasData = true,
): LucaGuideKpiTargetTone {
  if (
    !hasData ||
    current == null ||
    Number.isNaN(current) ||
    Number.isNaN(target)
  ) {
    return "secondary";
  }

  const isGood = lowerIsBetter ? current <= target : current >= target;
  if (isGood) {
    return "success";
  }

  const deviationPercent = Math.abs(((current - target) / target) * 100);
  return deviationPercent <= LUCA_GUIDE_KPI_NEAR_TARGET_PERCENT
    ? "warning"
    : "error";
}

/** Tailwind text class for a server-provided `good` flag. */
export function getLucaGuideKpiValueClass(
  good: boolean | null | undefined,
): string {
  if (good === true) {
    return "tw:text-success";
  }

  if (good === false) {
    return "tw:text-error";
  }

  return "tw:text-secondary-text";
}

/**
 * Campaign/account-level current value for a KPI, aggregated from classified ads.
 *
 * Source: guide-dev.hiluca.com/app inline script `campaignKpiValue(key, ads)`.
 * That helper only derives values from fields on `GET /api/v2/ads`
 * (`total_impressions`, `total_spend`, `total_conversions`, `ctr`, `cvr`).
 * Unsupported keys (most of the 67 KPI catalog) intentionally return `null`
 * and render as "—" — same as the reference app.
 */
export function computeAdsKpiValue(
  key: string,
  ads: Pick<
    LucaGuideAd,
    "total_impressions" | "total_spend" | "total_conversions" | "ctr" | "cvr"
  >[],
): number | null {
  if (ads.length === 0) {
    return null;
  }

  const impressions = ads.reduce((sum, ad) => sum + ad.total_impressions, 0);
  const spend = ads.reduce((sum, ad) => sum + ad.total_spend, 0);
  const conversions = ads.reduce((sum, ad) => sum + ad.total_conversions, 0);

  const weightedAverage = (field: "ctr" | "cvr") => {
    if (!impressions) {
      return null;
    }

    return (
      ads.reduce((sum, ad) => sum + ad[field] * ad.total_impressions, 0) /
      impressions
    );
  };

  switch (key) {
    case "ctr":
    case "link_ctr":
    case "outbound_ctr":
      return weightedAverage("ctr");
    case "cpm":
      return impressions ? (spend / impressions) * 1000 : null;
    case "cvr":
    case "conversion_rate":
      return weightedAverage("cvr");
    case "cpa":
    case "cac":
      return conversions ? spend / conversions : null;
    case "impressions":
      return impressions;
    case "spend":
      return spend;
    case "purchases":
    case "leads":
    case "messaging_conversations":
    case "messaging_conversations_started":
    case "engagements":
    case "results":
    case "conversions":
      // Ads list exposes a single conversions total; reference maps these keys to it.
      return conversions;
    default:
      return null;
  }
}

/**
 * Formats a KPI value. `value` may be a number (computed) or a decimal string
 * (north-star target). `null`, `undefined`, and `""` render as "—".
 * Currency and counts use full amounts (not K/M).
 *
 * @example
 * formatLucaGuideKpiValue(570.18, "currency", "en", "MXN") // "MX$570.18"
 * formatLucaGuideKpiValue(1500, "currency", "en", "MXN") // "MX$1,500.00"
 * formatLucaGuideKpiValue(2.46, "percent", "en") // "2.5%"
 * formatLucaGuideKpiValue(0.85, "percent", "en") // "0.85%"
 * formatLucaGuideKpiValue("1.2", "ratio", "en") // "1.2×"
 * formatLucaGuideKpiValue(1500, "count", "en") // "1,500"
 * formatLucaGuideKpiValue(12, "seconds", "en") // "12s"
 * formatLucaGuideKpiValue(null, "percent", "en") // "—"
 * formatLucaGuideKpiValue(undefined, "currency", "en") // "—"
 */
export function formatLucaGuideKpiValue(
  value: number | string | null | undefined,
  formatType: LucaGuideKpiFormatType | string | undefined,
  locale: string,
  currency?: string | null,
): string {
  return _formatLucaGuideKpiValueBase(
    value,
    formatType,
    locale,
    currency,
    false,
  );
}

/**
 * Same as {@link formatLucaGuideKpiValue}, with compact currency/count (K/M).
 *
 * @example
 * formatCompactLucaGuideKpiValue(1500, "currency", "en", "MXN") // "MX$1.5K"
 * formatCompactLucaGuideKpiValue(1500, "count", "en") // "1.5K"
 */
export function formatCompactLucaGuideKpiValue(
  value: number | string | null | undefined,
  formatType: LucaGuideKpiFormatType | string | undefined,
  locale: string,
  currency?: string | null,
): string {
  return _formatLucaGuideKpiValueBase(
    value,
    formatType,
    locale,
    currency,
    true,
  );
}

/**
 * Precision-aware percent rendering (HLG-177).
 *
 * `toFixed(1)` collapsed sub-1% rates: a saved Outbound-CTR target of `0.85`
 * displayed as `0.8%`. Sub-1% rates therefore keep a FIXED 2 decimals so they're
 * directly comparable (`0.85 → 0.85%`, `0.80 → 0.80%`, `0.797 → 0.80%`), while
 * values of 1% and above stay at 1 decimal (`2.46 → 2.5%`). Earlier this trimmed
 * trailing zeros (`Number(toFixed(2))`), which reintroduced the ambiguity it was
 * meant to fix — a 0.797% value rendered "0.8%" right next to a "0.85%" target.
 */
function formatPercentNumber(value: number): string {
  if (Math.abs(value) > 0 && Math.abs(value) < 1) {
    return value.toFixed(2);
  }

  return value.toFixed(1);
}

function _formatLucaGuideKpiValueBase(
  value: number | string | null | undefined,
  formatType: LucaGuideKpiFormatType | string | undefined,
  locale: string,
  currency: string | null | undefined,
  compact: boolean,
): string {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numeric)) {
    return "—";
  }

  switch (formatType) {
    case "currency":
      return compact
        ? formatCompactCurrency(numeric, locale, currency)
        : formatCurrencyValue(numeric, locale, currency);
    case "percent":
      return `${formatPercentNumber(numeric)}%`;
    case "multiplier":
    case "ratio":
      return `${numeric.toFixed(1)}×`;
    case "count":
    case "ranking":
      return compact
        ? formatCompactCount(numeric, locale)
        : formatNumberValue(numeric, locale);
    case "seconds": {
      const seconds = compact
        ? formatCompactCount(numeric, locale)
        : formatNumberValue(numeric, locale);
      return `${seconds}s`;
    }
    default:
      return String(numeric);
  }
}
