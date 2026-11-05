export const PAID_SOCIAL_CHANNEL_GROUP_NAME = "Paid Social";

export const ADS_ASSEMBLY_GENERATE_AD_VARIATIONS_JOB_POLLING_INTERVAL_MS =
  10 * SECOND_IN_MS;
export const ADS_ASSEMBLY_GENERATE_AD_VARIATIONS_JOB_TIMEOUT_MS = HOUR_IN_MS;

export const ADS_ASSEMBLY_EDIT_MEDIA_IMAGE_JOB_POLLING_INTERVAL_MS =
  5 * SECOND_IN_MS;
export const ADS_ASSEMBLY_EDIT_MEDIA_IMAGE_JOB_TIMEOUT_MS = 30 * MINUTE_IN_MS;

export const STRIP_LEADING_NUMBERS_FROM_AD_MEDIA_ELEMENT_NAME = true;

/**
 * When `true`, the image library modal of the static image flow's banner editor
 * offers the "Generate AI image" source. Set it to `false` to hide it.
 */
export const ADS_ASSEMBLY_ENABLE_GENERATE_AI_IMAGE_SOURCE = false;

export const ADS_ASSEMBLY_VIDEO_REFERENCE_IMAGE_MAX_FILE_SIZE_BYTES =
  60 * MB_IN_BYTES;
export const ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_MAX_FILE_SIZE_BYTES =
  60 * MB_IN_BYTES;

/**
 * Most reference images in Settings, from the Figma. Full Video uses the model's own limit
 * instead, when the catalogue gives one.
 */
export const ADS_ASSEMBLY_VIDEO_REFERENCE_IMAGES_MAX_COUNT = 10;

export const ADS_ASSEMBLY_VIDEO_REFERENCE_IMAGE_ACCEPTED_FORMATS = [
  "png" as const,
  "jpg" as const,
  "jpeg" as const,
  "webp" as const,
];
export const ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_ACCEPTED_FORMATS = [
  "mp4" as const,
  "mov" as const,
];

/**
 * The video generation flow is on by default in this environment (DEV and QAS set
 * VITE_ENABLE_VIDEO_GENERATION=true in their deploy workflows; production doesn't), so
 * testers don't have to add `?videoGeneration=true` to the URL.
 */
export const IS_VIDEO_GENERATION_ENABLED_BY_DEFAULT =
  import.meta.env.VITE_ENABLE_VIDEO_GENERATION === "true";

/**
 * When enabled, the Budget strategy section is shown in the Launchpad
 * technical configuration. Kept behind a flag until the back-end supports it.
 */
export const ENABLE_BUDGET_STRATEGY =
  import.meta.env.VITE_ENABLE_BUDGET_STRATEGY === "true";
