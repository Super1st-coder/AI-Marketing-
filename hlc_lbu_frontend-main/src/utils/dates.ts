import i18n from "@/plugins/i18n";

export function getShortDateFormatter(locale: string) {
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getDateRangeFormatter(locale: string) {
  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function parseIsoDate(value: string): Date {
  return new Date(value);
}

export function parseLocalIsoDate(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

export function formatLocalIsoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatDateRange(
  start: Date,
  end: Date,
  locale: string,
): string {
  return getDateRangeFormatter(locale).formatRange(start, end);
}

/** Compact relative time matching Luca Guide reference: `34m ago`, `13h ago`, `2d ago`. */
export function getCompactRelativeTimeParts(
  isoDate: string,
  now = Date.now(),
): { unit: "minutes" | "hours" | "days" | "just-now"; count: number } {
  const ms = now - new Date(isoDate).getTime();
  const seconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days >= 1) return { unit: "days", count: days };
  if (hours >= 1) return { unit: "hours", count: hours };
  if (minutes >= 1) return { unit: "minutes", count: minutes };
  return { unit: "just-now", count: 0 };
}

/** Formats compact relative time using `global.relative-time.*` translations. */
export function formatCompactRelativeTime(
  isoDate: string,
  now = Date.now(),
): string {
  const parts = getCompactRelativeTimeParts(isoDate, now);

  return i18n.global.t(`global.relative-time.${parts.unit}`, {
    count: parts.count,
  });
}
