export const BRAND_DATA_SOURCE_MAX_FILE_SIZE_BYTES = 50 * MB_IN_BYTES;
export const BRAND_LOGO_MAX_FILE_SIZE_BYTES = 10 * MB_IN_BYTES;
export const BRAND_TYPOGRAPHY_MAX_FILE_SIZE_BYTES = 25 * MB_IN_BYTES;
export const BRAND_DOS_DONTS_IMAGE_MAX_FILE_SIZE_BYTES = 25 * MB_IN_BYTES;

export const BRAND_LOGO_ACCEPTED_FORMATS = [
  "png" as const,
  "jpg" as const,
  "jpeg" as const,
  "webp" as const,
];
export const BRAND_DATA_SOURCE_ACCEPTED_FORMATS = ["pdf" as const];
export const BRAND_TYPOGRAPHY_ACCEPTED_FORMATS = [
  "ttf" as const,
  "otf" as const,
  "woff" as const,
  "woff2" as const,
];

export const BRAND_CREATION_RING_LOADER_INTERVAL_MS = 10 * SECOND_IN_MS;
export const BRAND_EDITION_RING_LOADER_INTERVAL_MS = 10 * SECOND_IN_MS;
export const BRAND_NEW_CONTEXT_RING_LOADER_INTERVAL_MS = 10 * SECOND_IN_MS;
export const BRAND_RING_LOADER_COMPLETION_HOLD_MS = 4 * SECOND_IN_MS;
