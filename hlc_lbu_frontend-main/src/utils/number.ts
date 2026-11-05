export function castStringToNumber(value: string | undefined | null | number) {
  if (!value) {
    return 0;
  }

  if (typeof value === "number") {
    return value;
  }

  const castedValue = parseFloat(value);
  return isNaN(castedValue) ? 0 : castedValue;
}

export const formatFileSize = (size: number): string => {
  const units = ["Bytes", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(1)} ${units[i]}`;
};

export function formatNumberValue(value: number, locale: string): string {
  return new Intl.NumberFormat(locale).format(value);
}

export function formatPercentValue(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value / 100);
}

/**
 * Locale to use for the currency SYMBOL so non-home currencies disambiguate (USD → "US$",
 * MXN → "MX$") instead of a bare, ambiguous "$". English (home currency = USD) renders USD as a
 * plain "$", which reads as MXN to a Mexican client; en-GB prefixes the ISO symbol while keeping
 * English digit grouping ("US$1,500.00"). Spanish already disambiguates, so it's left untouched.
 * (Marco #15: currency showed correctly in Español but a bare "$" in English.)
 */
function currencySymbolLocale(locale: string): string {
  return locale.toLowerCase().startsWith("en") ? "en-GB" : locale;
}

export function formatCurrencyValue(
  value: number,
  locale: string,
  currency?: string | null,
  onlyNumber?: boolean,
): string {
  const { digits, code } = getCurrencyInfo(currency);

  try {
    return new Intl.NumberFormat(currencySymbolLocale(locale), {
      style: "currency",
      currency: onlyNumber ? undefined : code,
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(value);
  } catch {
    return value.toLocaleString(locale, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
}

/**
 * Formats a currency amount, switching to compact notation from 1,000 up.
 *
 * @example
 * formatCompactCurrency(0.45, "en", "MXN")    // "MX$0.45"
 * formatCompactCurrency(7.5, "en", "MXN")     // "MX$7.50"
 * formatCompactCurrency(42.5, "en", "MXN")    // "MX$42.50"
 * formatCompactCurrency(150, "en", "MXN")     // "MX$150"
 * formatCompactCurrency(1500, "en", "MXN")    // "MX$1.5K"
 * formatCompactCurrency(15000, "en", "MXN")   // "MX$15K"
 * formatCompactCurrency(1500000, "en", "MXN") // "MX$1.5M"
 */
export function formatCompactCurrency(
  value: number,
  locale: string,
  currency?: string | null,
): string {
  const { code } = getCurrencyInfo(currency);
  const abs = Math.abs(value);
  const compact = abs >= 1000;

  try {
    return new Intl.NumberFormat(currencySymbolLocale(locale), {
      style: "currency",
      currency: code,
      notation: compact ? "compact" : "standard",
      // Compact: keep one digit so 1500 → 1.5K (not 2K).
      // Standard: drop cents once values hit hundreds.
      maximumFractionDigits: compact ? 1 : abs >= 100 ? 0 : 2,
    }).format(value);
  } catch {
    return value.toLocaleString(locale, {
      maximumFractionDigits: 2,
    });
  }
}

export function formatCompactCount(value: number, locale: string): string {
  try {
    return new Intl.NumberFormat(locale, {
      notation: Math.abs(value) >= 1000 ? "compact" : "standard",
      maximumFractionDigits: 1,
    }).format(value);
  } catch {
    return String(Math.round(value));
  }
}

/**
 * Sorts numbers ascending and keeps null/undefined last.
 * When `descending` is true (Vuetify DataTable swaps the pair for desc),
 * nulls still sort last on screen.
 */
export function compareNullableNumbers(
  a: number | null | undefined,
  b: number | null | undefined,
  descending = false,
): number {
  if (a == null && b == null) {
    return 0;
  }

  if (a == null) {
    return descending ? -1 : 1;
  }

  if (b == null) {
    return descending ? 1 : -1;
  }

  return a - b;
}
