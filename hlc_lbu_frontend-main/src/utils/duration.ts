export type DurationFormatterInput = {
  hours?: number;
  minutes?: number;
  seconds?: number;
};

export function formatRemainingDuration(
  locale: string,
  remainingMs: number,
): string {
  // Calculate hours, minutes, and seconds from the remaining milliseconds
  const totalSeconds = Math.max(0, Math.ceil(remainingMs / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  // Create a duration object for Intl.DurationFormat
  const duration: DurationFormatterInput = { seconds };
  if (minutes > 0 || hours > 0) {
    duration.minutes = minutes;
  }
  if (hours > 0) {
    duration.hours = hours;
  }

  // Check if Intl.DurationFormat is supported
  const DurationFormatCtor = Reflect.get(Intl, "DurationFormat");
  if (typeof DurationFormatCtor === "function") {
    const formatter = new DurationFormatCtor(locale, {
      style: "long",
    }) as { format: (duration: DurationFormatterInput) => string };

    return formatter.format(duration);
  }

  // Fallback for environments without Intl.DurationFormat support
  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  parts.push(`${seconds}s`);

  return parts.join(" ");
}

export function formatDurationDigital(
  locale: string,
  totalSeconds: number,
): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  // Check if Intl.DurationFormat is supported
  const DurationFormatCtor = Reflect.get(Intl, "DurationFormat");
  if (typeof DurationFormatCtor === "function") {
    const formatter = new DurationFormatCtor(locale, {
      style: "digital",
      hoursDisplay: "auto",
    }) as { format: (duration: DurationFormatterInput) => string };

    return formatter.format({ minutes, seconds });
  }

  // Fallback for environments without Intl.DurationFormat support
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
