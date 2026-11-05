import { handleCommonErrors } from "../common-errors";
import type { BaseApiResponseData } from "@/utils/type-declarations";
import type {
  AdMediaBanner,
  AdChannelAttribute,
  AdMediaDefinition,
} from "./paid-social/AdsApi";
import type { AudienceItem } from "../projects/AudienceApi";
import type { AdsExperimentByAdSetData } from "./paid-social/AdsExperiment";

export type FunnelFlowValidatorStateError = {
  message: string;
  code: string;
  metadata?: Record<string, string>;
};

export type FunnelFlowValidatorState = {
  step: string;
  completed: boolean;
  errors: FunnelFlowValidatorStateError[];
};

export type FunnelFlowValidatorMediaBanner = AdMediaBanner & {
  bucket: string | null;
  image_id: string | null;
  thumbnail_id: string | null;
};

export type FunnelFlowValidatorMedia = Pick<
  AdMediaDefinition,
  "template_id" | "elements" | "formats"
> & {
  images_banner: FunnelFlowValidatorMediaBanner[] | null;
};

export type FunnelFlowValidatorAdChannel = {
  channel_id: number;
  channel_name: string;
  media: FunnelFlowValidatorMedia;
  /** Null while the ad has no content yet */
  channel_attributes: AdChannelAttribute[] | null;
  url: string | null;
};

export type FunnelFlowValidatorAdAttributes = {
  name: string;
  ad_channels: FunnelFlowValidatorAdChannel[];
};

export type FunnelFlowValidatorAd = {
  id: number;
  attributes: FunnelFlowValidatorAdAttributes;
};

export type FunnelFlowValidatorAudience = {
  channel_id: number;
  channel_name: string;
  generation_method: string;
  preferred_audience: AudienceItem;
  proposal_audiences: AudienceItem[];
};

export type FunnelFlowValidatorExperiment = Omit<
  AdsExperimentByAdSetData,
  "ad_set_id"
> & {
  subcategory: {
    id: number;
    name: string;
    description: string | null;
    category: {
      id: number;
      name: string;
      description: string | null;
    };
  };
};

export type FunnelFlowValidatorAdSet = {
  id: number;
  name: string;
  /** Abyssale project linked in the Asset Origin screen, null until picked */
  media_platform_project_id: string | null;
  ads: FunnelFlowValidatorAd[];
  audiences: FunnelFlowValidatorAudience[];
  experiments: FunnelFlowValidatorExperiment[];
};

export type FunnelFlowValidator = {
  state: FunnelFlowValidatorState[];
  funnel_flow_data: FunnelFlowValidatorAdSet[];
};

export type FunnelFlowValidatorResponse =
  BaseApiResponseData<FunnelFlowValidator>;

export default {
  async getValidatorResults(
    campaign_id: number,
  ): Promise<FunnelFlowValidatorResponse> {
    try {
      return await $api<FunnelFlowValidatorResponse>(
        `v2/external/funnel_flow/validator/${campaign_id}`,
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
