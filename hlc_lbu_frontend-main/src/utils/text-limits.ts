export function getWarningLimit(base: number) {
  const extra = Math.min(Math.ceil(base * 0.2), 10);
  return base + extra;
}
