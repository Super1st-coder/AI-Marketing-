/** Primary paid-social ad channel (formerly "Instagram"). */
export const META_ADS_CHANNEL_NAME = "Meta Ads";

/**
 * Max length for Meta ad set and ad names (kept short for Ads Manager readability).
 * Meta API hard limit is 400 chars — see:
 * - Ad set: https://developers.facebook.com/docs/marketing-api/reference/ad-campaign/
 * - Ad: https://developers.facebook.com/docs/marketing-api/reference/adgroup/
 */
export const META_ADS_MAX_NAME_LENGTH = 60;
