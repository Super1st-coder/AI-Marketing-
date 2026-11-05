// Thresholds from the backend docs: green >= 8, orange 6-7.9, red < 6
export function videoScriptScoreColorClass(value: number | null) {
  if (value === null) return undefined;
  if (value >= 8) return "tw:text-success";
  if (value >= 6) return "tw:text-warning";
  return "tw:text-error";
}
