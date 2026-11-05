import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleCommonErrors } from "../../common-errors";
import { getWarningLimit } from "@/utils/text-limits";
import { TaskStartResponse } from "../../UtilsApi";
import type {
  GenerateAdVariationsJobResultData,
  GenerateAdVariationsJobResultSuccess,
} from "./AdStructureApi";
import type { VideoDraft, VideoDraftAssembledVideo } from "./VideoApi";

export type AdMediaTemplate = {
  template_id: string;
  template_name: string;
  template_preview_url: string;
  type: "static";
};

export type AdMediaElement = {
  name: string;
  type: string;
  payload: string;
  intention: string | null;
  original_payload: string;
  max_char?: number;
};

export type AdImagePrompt = {
  id: number;
  preferred: number;
  description: string;
};

export type AdImageAttributes = {
  place: string;
  emotion: string;
  core_idea: string;
  primary_visual: string;
  target_audience: string;
};

export type AdMediaBanner = {
  name: string;
  type: string;
  preview_url: string;
  image_prompts: AdImagePrompt[] | null;
  image_style_id: number | null;
  image_attributes_saved: AdImageAttributes | null;
  preferred_image_prompt: AdImagePrompt | null;
  image_attributes_generated: AdImageAttributes | null;
  /** Library ID of the image currently assigned to the banner */
  image_id?: string | null;
};

export type AdMediaFormat = {
  id: string;
  uid: string;
  unit: string;
  width: number;
  height: number;
  pinned?: boolean;
  preview_url: string;
  visual_id?: string | null;
  visual_url?: string | null;
  errors?: string[] | null;
};

export type AdChannelAttributePayload = {
  id: number;
  payload: string;
};

// This needs to be updated when the types are updated in the backend
export const adChannelAttributeTypes = ["text", "button"] as const;
export type AdChannelAttributeType = (typeof adChannelAttributeTypes)[number];

export type AdChannelAttribute = {
  id: number;
  max: number;
  min: number;
  name: string;
  type: AdChannelAttributeType;
  max_char: number;
  payloads: (AdChannelAttributePayload | null)[];
  display_name: string;
};

export type AdMediaDefinition = {
  template_id: string | null;
  platform_project_id: string | null;
  template_name: string | null;
  elements: AdMediaElement[] | null;
  images_banner: AdMediaBanner[] | null;
  formats: AdMediaFormat[] | null;
  generated: boolean | null;
  generation_request_pending: boolean | null;
  generation_request_datetime: string | null;
  request_datetime: string | null;
};

export type AdVariant = {
  id: number;
  selected: boolean;
  media: AdMediaDefinition;
  channel_attributes: AdChannelAttribute[] | null;
};

export type AdChannelDefinition = {
  channel_id: number;
  channel_name: string;
  audience: null;
  experiment: null;
  variants: AdVariant[];
};

export type AdByCampaignDefinitionData = {
  ad_id: number;
  ad_name: string;
  ad_channels: AdChannelDefinition[];
  url: string | null;
};

export type ResetAdsBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  channel_id: number;
};

export type SelectAdVariantBody = {
  brand_id: number;
  campaign_id: number;
  ad_id: number;
  channel_id: number;
  variant_id: number;
};

export type PinAdVariantFormatBody = {
  brand_id: number;
  campaign_id: number;
  ad_id: number;
  channel_id: number;
  variant_id: number;
  format_id: string;
};

export type DeleteAdVariantBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  channel_id: number;
  variant_id: number;
};

export type GenerateSingleAdVariantBody = {
  brand_id: number;
  campaign_id: number;
  ad_id: number;
  channel_id: number;
  variant_id: number | null;
  add_variant: boolean;
  custom_prompt: string;
};

export type GenerateAdVariantListBody = {
  brand_id: number;
  campaign_id: number;
  ad_id: number;
  channel_id: number;
  add_variant: boolean;
  custom_prompt: string;
  n_variants: number;
};

export type AdEditMediaImageBody = {
  brand_id: number;
  campaign_id: number;
  ad_id: number;
  channel_id: number;
  variant_id: number;
  image_name: string;
  /** Library ID of the base image to edit */
  image_id: string;
  n_variations: number;
  custom_prompt: string | null;
  expand_zoom_option: ImageStudioExpandZoom | null;
};

export type AdEditMediaImageVariation = {
  id: string;
  url: string;
  prompt: string;
};

export type AdEditMediaImageJobResultSuccess = Omit<
  GenerateAdVariationsJobResultSuccess,
  "result"
> & {
  result: {
    task_id: string;
    variant_id: number;
    id_base_image: string;
    status: "DONE";
    variations: AdEditMediaImageVariation[];
  };
};

export type AdEditMediaImageJobResultData =
  | Exclude<
      GenerateAdVariationsJobResultData,
      GenerateAdVariationsJobResultSuccess
    >
  | AdEditMediaImageJobResultSuccess;

export type AdEditMediaImageJobResult =
  BaseApiResponseData<AdEditMediaImageJobResultData>;

export type AdByCampaignDefinitionResponse =
  BaseApiResponseData<AdByCampaignDefinitionData>;

export type AdMediaTemplateListResponse = BaseApiResponseData<
  AdMediaTemplate[]
>;

export type AdSetMediaTemplateResponse = BaseApiResponseData<{
  ad_id: number;
  ad_name: string;
  channel_id: number;
  channel_name: string;
  media: AdMediaDefinition;
}>;

export type GenerateTextForMediaElementResponse = BaseApiResponseData<{
  name: string;
  type: string;
  payload: string[];
  intention: string | null;
  original_payload: string;
}>;

export type GenerateTextsForMediaElementsResponse = BaseApiResponseData<
  Array<{
    name: string;
    type: string;
    payload: string | string[];
    intention: string | null;
    original_payload: string;
    max_char?: number;
  }>
>;

export type AdSaveMediaElementsResponse = BaseApiResponseData<{
  brand_id: number;
  campaign_id: number;
  ad_id: number;
  channel_id: number;
  media: Pick<AdMediaDefinition, "template_id" | "template_name" | "elements">;
}>;

export type AdSetMediaImageStyleResponse = BaseApiResponseData<{
  ad_id: number;
  ad_name: string;
  channel_id: number;
  channel_name: string;
  media: Pick<
    AdMediaDefinition,
    "template_id" | "template_name" | "images_banner"
  >;
}>;

export type AdGenerateMediaImageAttributesResponse = BaseApiResponseData<{
  ad_id: number;
  ad_name: string;
  channel_id: number;
  channel_name: string;
  media: Pick<
    AdMediaDefinition,
    "template_id" | "template_name" | "images_banner"
  >;
}>;

export type AdSaveMediaImageAttributesResponse = BaseApiResponseData<{
  ad_id: number;
  ad_name: string;
  channel_id: number;
  channel_name: string;
  media: Pick<
    AdMediaDefinition,
    "template_id" | "template_name" | "images_banner"
  >;
}>;

export type AdGenerateMediaImagePromptsResponse = BaseApiResponseData<{
  ad_id: number;
  ad_name: string;
  channel_id: number;
  channel_name: string;
  media: Pick<
    AdMediaDefinition,
    "template_id" | "template_name" | "images_banner"
  >;
}>;

export type AdSavePreferredMediaImagePromptResponse = BaseApiResponseData<{
  ad_id: number;
  ad_name: string;
  channel_id: number;
  channel_name: string;
  media: Pick<
    AdMediaDefinition,
    "template_id" | "template_name" | "images_banner"
  >;
}>;

export type GenerateTextForAdChannelAttributeResponse = BaseApiResponseData<{
  id: number;
  name: string;
  payload: string[];
}>;

export type GenerateTextsForAdChannelAttributeResponse = BaseApiResponseData<
  { id: number; name: string; payloads: { id: number; payload: string[] }[] }[]
>;

export function getAdMediaElementDisplayName(name: string) {
  const baseName = STRIP_LEADING_NUMBERS_FROM_AD_MEDIA_ELEMENT_NAME
    ? name.replace(/^\d+[-_]?/, "")
    : name;

  return anyCaseToText(baseName);
}

export function isVisualGenerationPending(media: AdMediaDefinition) {
  const {
    generation_request_pending,
    generation_request_datetime,
    request_datetime,
  } = media;

  const isGreaterThanOneMinute = (() => {
    if (!generation_request_datetime) return true;
    if (!request_datetime) return true;

    return (
      new Date(request_datetime).getTime() -
        new Date(generation_request_datetime).getTime() >
      30_000
    );
  })();

  return Boolean(generation_request_pending) && !isGreaterThanOneMinute;
}

export function getChannelSelectedVariant(channel: AdChannelDefinition) {
  if (channel.variants.length === 0) {
    return undefined;
  }

  const selectedVariant = channel.variants.find((variant) => variant.selected);
  return selectedVariant;
}

export function validateMediaElement(element: AdMediaElement) {
  if (!element.intention || !element.payload) {
    return false;
  }

  // If there's no original payload, do not limit the character length
  if (!element.original_payload) {
    return true;
  }

  // Extract the original payload length and use it as the maximun character count
  const length = getWarningLimit(element.original_payload.length);
  if (element.payload.length > length) {
    return false;
  }

  return true;
}

export function isMediaCompleted(media: AdMediaDefinition): boolean {
  const hasMedia =
    // Check if media has formats
    media.formats &&
    media.formats.length > 0 &&
    // Check if the elements has been set
    media.elements &&
    media.elements.every((element) => validateMediaElement(element)) &&
    // Check if the there aren't formats with errors
    !media.formats.some((format) => format.errors && format.errors.length > 0);

  return !!hasMedia;
}

export function doesVariantHaveValidMedia(variant: AdVariant | undefined) {
  if (!variant) {
    return false;
  }

  const hasMedia = isMediaCompleted(variant.media);
  return hasMedia;
}

export function doesVariantHavePinnedFormat(variant: AdVariant | undefined) {
  return !!getPinnedFormat(variant?.media.formats);
}

export function isChannelAttributeValid(
  attribute: AdChannelAttribute | undefined,
) {
  if (!attribute) {
    return false;
  }

  // The attribute is not valid if it doesn't have any payload
  if (attribute.payloads.length === 0) {
    return false;
  }

  const maxCharacters = attribute.max_char;

  // The attribute is not valid if any of its payloads is
  // empty or exceeds the max character limit
  return attribute.payloads
    .filter((payload): payload is AdChannelAttributePayload => Boolean(payload))
    .every(({ payload }) => {
      if (!payload) {
        return false;
      }

      if (maxCharacters && payload.length > maxCharacters) {
        return false;
      }

      return true;
    });
}

// A variant without texts isn't valid either: they're required to publish it
export function doesVariantHaveValidAttributes(variant: AdVariant | undefined) {
  if (!variant?.channel_attributes?.length) {
    return false;
  }

  return variant.channel_attributes.every((attribute) =>
    isChannelAttributeValid(attribute),
  );
}

/**
 * @param video For a variant of the video flow, which has a video instead of a
 * banner (so no media or pinned format to check): its finished video, or `null`
 * if it doesn't have one yet. Leave it out for an image variant.
 */
export function isVariantCompleted(
  variant: AdVariant | undefined,
  video?: VideoDraftAssembledVideo | null,
) {
  if (variant === undefined) {
    return false;
  }

  const hasValidVisual =
    video === undefined
      ? doesVariantHaveValidMedia(variant) &&
        doesVariantHavePinnedFormat(variant)
      : video !== null;

  return hasValidVisual && doesVariantHaveValidAttributes(variant);
}

/**
 * The finished video of a variant of a video ad, if it has one. The draft maps
 * each of its variants to the variant's id in `variant_rows`.
 */
export function getVariantVideo(variantId: number, videoDraft: VideoDraft) {
  const draftVariantId = Object.keys(videoDraft.variant_rows).find(
    (key) => videoDraft.variant_rows[key] === variantId,
  );

  const video = draftVariantId
    ? videoDraft.variants[draftVariantId]?.video
    : undefined;

  // The storage fields are left out when the video couldn't be stored
  return video?.storage_key || video?.storage_path ? video : undefined;
}

/**
 * @param videoDraft The saved progress of a video ad. When it exists, the
 * selected variant is checked with its video (see `isVariantCompleted`).
 */
export function isChannelCompleted(
  ad: Pick<AdByCampaignDefinitionData, "url">,
  channel: AdChannelDefinition,
  videoDraft?: VideoDraft,
) {
  const selectedVariant = getChannelSelectedVariant(channel);

  return (
    selectedVariant !== undefined &&
    !!ad.url &&
    isVariantCompleted(
      selectedVariant,
      videoDraft?.exists
        ? (getVariantVideo(selectedVariant.id, videoDraft) ?? null)
        : undefined,
    )
  );
}

/**
 * @param videoDraft The saved progress of a video ad, if it is one.
 */
export function isAdCompleted(
  ad: AdByCampaignDefinitionData,
  videoDraft?: VideoDraft,
) {
  return (
    ad.ad_channels.length > 0 &&
    ad.ad_channels.every((channel) =>
      isChannelCompleted(ad, channel, videoDraft),
    ) &&
    !!ad.url
  );
}

export function getPinnedFormat(
  formats: AdMediaFormat[] | null | undefined,
): AdMediaFormat | undefined {
  return formats?.find((format) => format.pinned);
}

export function getNearestFormatFromAspectRatio(
  formats: AdMediaFormat[] | null | undefined,
  aspectRatio: number,
): AdMediaFormat | undefined {
  if (!formats || !Array.isArray(formats) || formats.length === 0) {
    return undefined;
  }

  let nearestFormat: AdMediaFormat | undefined;
  let nearestDistance = Infinity;

  for (const format of formats) {
    const { width, height } = format;
    if (!width || !height) continue;

    const distanceFromTarget = Math.abs(width / height - aspectRatio);
    if (distanceFromTarget < nearestDistance) {
      nearestDistance = distanceFromTarget;
      nearestFormat = format;
    }
  }

  return nearestFormat;
}

export function getPinnedOrNearestFourFiveFormat(
  formats: AdMediaFormat[] | null | undefined,
): AdMediaFormat | undefined {
  return (
    getPinnedFormat(formats) ?? getNearestFormatFromAspectRatio(formats, 4 / 5)
  );
}

export function getPinnedOrNearestFourFiveFormatIndex(
  formats: AdMediaFormat[] | null | undefined,
): number {
  if (!formats?.length) return 0;

  const format = getPinnedOrNearestFourFiveFormat(formats);
  if (!format) return 0;

  const index = formats.indexOf(format);
  return index >= 0 ? index : 0;
}

export function getNearestImageFromFormats(
  formats: AdMediaFormat[] | null | undefined,
  aspectRatio: number,
) {
  const nearestFormat = getNearestFormatFromAspectRatio(formats, aspectRatio);

  if (nearestFormat) {
    return nearestFormat.visual_url ?? nearestFormat.preview_url;
  }

  return formats?.[0]?.visual_url ?? formats?.[0]?.preview_url;
}

export function getNearestSquareImageFromFormats(
  formats: AdMediaFormat[] | null | undefined,
) {
  return getNearestImageFromFormats(formats, 1 / 1);
}

export function getPinnedOrNearestFourFiveImageFromFormats(
  formats: AdMediaFormat[] | null | undefined,
) {
  const format = getPinnedOrNearestFourFiveFormat(formats) ?? formats?.[0];

  return format?.visual_url ?? format?.preview_url;
}

export default {
  async getOneAd(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    options?: { signal?: AbortSignal },
  ): Promise<AdByCampaignDefinitionResponse> {
    try {
      return await $api<AdByCampaignDefinitionResponse>(
        `/v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/ad/${ad_id}`,
        {
          method: "GET",
          // Pass through the signal when provided so callers can abort
          signal: options?.signal,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getMediaTemplates(
    brand_id: number,
    campaign_id: number,
    template_id: string,
  ): Promise<AdMediaTemplateListResponse> {
    try {
      return await $api<AdMediaTemplateListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/ad/media/templates/${template_id}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);

      throw error;
    }
  },

  async setMediaTemplate(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    media_platform_project_id: string,
    media_template_id: string,
  ): Promise<AdSetMediaTemplateResponse> {
    try {
      return await $api<AdSetMediaTemplateResponse>(
        "/v2/application/hiluca/brand/ad/media/template",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            media_platform_project_id,
            media_template_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateTextForMediaElement(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    data: {
      element: AdMediaElement;
    },
  ): Promise<GenerateTextForMediaElementResponse> {
    try {
      return await $api<GenerateTextForMediaElementResponse>(
        "/v2/application/hiluca/brand/ad/media/elements/generate_text",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateTextsForMediaElements(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    data: {
      elements: AdMediaElement[];
    },
  ): Promise<GenerateTextsForMediaElementsResponse> {
    try {
      return await $api<GenerateTextsForMediaElementsResponse>(
        "/v2/application/hiluca/brand/ad/media/elements/generate_texts",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveMediaElements(
    data: {
      brand_id: number;
      campaign_id: number;
      ad_id: number;
      channel_id: number;
      variant_id: number;
      elements: AdMediaElement[];
    },
    options?: { signal?: AbortSignal },
  ): Promise<AdSaveMediaElementsResponse> {
    try {
      return await $api<AdSaveMediaElementsResponse>(
        "/v2/application/hiluca/brand/ad/media/elements",
        {
          method: "POST",
          body: {
            ...data,
          },
          signal: options?.signal,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateAbyssaleMediaVisuals(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    data: {
      elements: AdMediaElement[];
    },
  ): Promise<BaseApiResponseData<{}>> {
    try {
      return await $api<BaseApiResponseData<{}>>(
        "/v2/application/hiluca/brand/ad/media/visuals/generate",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getMediaImage(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    image_name: string,
  ): Promise<Blob | undefined> {
    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/ad/${ad_id}/channel/${channel_id}/variant/${variant_id}/media/images/${image_name}`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );
    } catch (error: any) {
      return undefined;
    }
  },

  async uploadMediaImageFromImgLibrary(data: {
    brand_id: number;
    campaign_id: number;
    ad_id: number;
    channel_id: number;
    variant_id: number;
    image_name: string;
    image_id: string;
  }): Promise<void> {
    try {
      await $api(
        "/v2/application/hiluca/brand/campaign/ad/channel/media/images",
        {
          method: "POST",
          body: data,
        },
      );

      return;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadMediaImage(
    data: {
      brand_id: number;
      campaign_id: number;
      ad_id: number;
      channel_id: number;
      variant_id: number;
      image_name: string;
      image: Blob;
    },
    options?: { signal?: AbortSignal },
  ): Promise<void> {
    const formData = new FormData();
    formData.append("file", data.image);

    try {
      await $api(
        `/v2/application/hiluca/brand/${data.brand_id}/campaign/${data.campaign_id}/ad/${data.ad_id}/channel/${data.channel_id}/variant/${data.variant_id}/media/images/${data.image_name}`,
        {
          method: "POST",
          body: formData,
          signal: options?.signal,
        },
      );

      return;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setMediaImageStyle(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    image_name: string,
    image_style_id: number,
  ): Promise<AdSetMediaImageStyleResponse> {
    try {
      return await $api<AdSetMediaImageStyleResponse>(
        "/v2/application/hiluca/brand/ad/media/images/style",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            image_name,
            image_style_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateMediaImageAttributes(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    image_name: string,
    data: { elements: AdMediaElement[] },
  ): Promise<AdGenerateMediaImageAttributesResponse> {
    try {
      return await $api<AdGenerateMediaImageAttributesResponse>(
        "/v2/application/hiluca/brand/ad/media/images/attributes/generate",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            image_name,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveMediaImageAttributes(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    image_name: string,
    data: {
      image_attributes_saved: AdImageAttributes;
      image_attributes_generated: AdImageAttributes;
    },
  ): Promise<AdSaveMediaImageAttributesResponse> {
    try {
      return await $api<AdSaveMediaImageAttributesResponse>(
        "/v2/application/hiluca/brand/ad/media/images/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            image_name,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateMediaImagePrompts(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    image_name: string,
    data: {
      elements: AdMediaElement[];
    },
  ): Promise<AdGenerateMediaImagePromptsResponse> {
    try {
      return await $api<AdGenerateMediaImagePromptsResponse>(
        "/v2/application/hiluca/brand/ad/media/images/prompts/generate",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            image_name,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveMediaImagePreferredPrompt(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    image_name: string,
    data: ImagePrompt,
  ): Promise<AdSavePreferredMediaImagePromptResponse> {
    try {
      return await $api<AdSavePreferredMediaImagePromptResponse>(
        "/v2/application/hiluca/brand/ad/media/images/prompts/preferred",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            image_name,
            preferred_image_prompt: data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setAdName({
    brand_id,
    campaign_id,
    ad_id,
    name,
  }: {
    brand_id: number;
    campaign_id: number;
    ad_id: number;
    name: string;
  }): Promise<void> {
    try {
      return await $api<void>(`/v2/application/hiluca/brand/ad/${ad_id}`, {
        method: "PUT",
        body: {
          brand_id,
          campaign_id,
          ad_id,
          name,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setAdRedirectUrl({
    brand_id,
    campaign_id,
    ad_id,
    redirect_url,
  }: {
    brand_id: number;
    campaign_id: number;
    ad_id: number;
    redirect_url: string;
  }): Promise<void> {
    try {
      return await $api<void>(
        "/v2/application/hiluca/brand/ad/channel/redirect_url",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            redirect_url,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveAdChannelAttributes(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    data: {
      attributes: AdChannelAttribute[];
    },
  ): Promise<AdSavePreferredMediaImagePromptResponse> {
    try {
      return await $api<AdSavePreferredMediaImagePromptResponse>(
        "/v2/application/hiluca/brand/ad/channel/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateTextForAdChannelAttribute(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    data: {
      attribute: AdChannelAttribute;
    },
  ): Promise<GenerateTextForAdChannelAttributeResponse> {
    try {
      return await $api<GenerateTextForAdChannelAttributeResponse>(
        "/v2/application/hiluca/brand/ad/channel/attributes/generate_text",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateTextsForAdChannelAttributes(
    brand_id: number,
    campaign_id: number,
    ad_id: number,
    channel_id: number,
    variant_id: number,
    data: {
      attributes: AdChannelAttribute[];
    },
  ): Promise<GenerateTextsForAdChannelAttributeResponse> {
    try {
      return await $api<GenerateTextsForAdChannelAttributeResponse>(
        "/v2/application/hiluca/brand/ad/channel/attributes/generate_texts",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_id,
            channel_id,
            variant_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async resetAds(body: ResetAdsBody): Promise<BaseApiResponseData<[]>> {
    try {
      return await $api<BaseApiResponseData<[]>>(
        "v2/application/hiluca/brand/audience/reset_ads",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async selectAdVariant(
    body: SelectAdVariantBody,
  ): Promise<BaseApiResponseData<[]>> {
    try {
      return await $api<BaseApiResponseData<[]>>(
        "v2/application/hiluca/brand/ad/variant/select",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async pinAdVariantFormat(
    body: PinAdVariantFormatBody,
  ): Promise<BaseApiResponseData<[]>> {
    try {
      return await $api<BaseApiResponseData<[]>>(
        "v2/application/hiluca/brand/ad/variant/pin_format",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async deleteAdVariant(
    body: DeleteAdVariantBody,
  ): Promise<BaseApiResponseData<[]>> {
    try {
      return await $api<BaseApiResponseData<[]>>(
        `v2/application/hiluca/brand/ad/variant/${body.variant_id}`,
        {
          body,
          method: "DELETE",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async startGenerateSingleAdVariantJob(
    body: GenerateSingleAdVariantBody,
  ): Promise<TaskStartResponse> {
    try {
      return await $api<TaskStartResponse>(
        "v2/application/hiluca/brand/ad/variant/generate",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async startGenerateAdVariantListJob(
    body: GenerateAdVariantListBody,
  ): Promise<TaskStartResponse> {
    try {
      return await $api<TaskStartResponse>(
        "v2/application/hiluca/brand/ad/variant/generate_all",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  /**
   * Starts an async job that edits a banner image of an ad variant and
   * generates `n_variations` edited images. Poll the result with
   * `getEditMediaImageJobResult`.
   */
  async startEditMediaImageJob(
    body: AdEditMediaImageBody,
  ): Promise<TaskStartResponse> {
    try {
      return await $api<TaskStartResponse>(
        "/v2/application/hiluca/brand/campaign/ad/channel/media/image/edit",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getEditMediaImageJobResult(
    jobId: string,
  ): Promise<AdEditMediaImageJobResult> {
    try {
      return await $api<AdEditMediaImageJobResult>(
        `/v2/application/hiluca/job/${jobId}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
