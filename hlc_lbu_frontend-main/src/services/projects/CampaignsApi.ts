import { handleCommonErrors } from "../common-errors";
import { ChannelGroupData, FunnelData, MetricData } from "../UtilsApi";
import {
  CreativeConceptData,
  CreativeConceptImageAttributes,
} from "./CreativeConceptsApi";
import { UmbrellaCampaignData } from "./UmbrellaCampaignsApi";

export type CampaignChannelGroupMetric = Partial<
  Pick<
    MetricData,
    "name" | "display_name" | "unit" | "value" | "type" | "target" | "group"
  >
> &
  Pick<MetricData, "group">;

export type CampaignChannelGroupData = Omit<ChannelGroupData, "active"> & {
  metrics?: CampaignChannelGroupMetric[] | null;
};

export type CampaingDetailsSectionData = {
  text: string;
  title: string;
};

export type CampaingDetailsData = {
  id: number;
  campaign: {
    title: string;
  };
  sections: {
    budget: CampaingDetailsSectionData;
    campaign_details: CampaingDetailsSectionData;
    creative_types: CampaingDetailsSectionData;
    cta: CampaingDetailsSectionData;
    execution_steps: CampaingDetailsSectionData;
    funnel_flow: CampaingDetailsSectionData;
    short_description: CampaingDetailsSectionData;
  };
  preferred: number;
};

export type SummaryCampaignData = {
  bperson: {
    persona_journey: string;
    persona_profile: string;
    persona_challenges: string;
    persona_motivation: string;
  };
  product: {
    core_incentive_offer: string;
    problem_solution_fit: string;
    emotional_outcome_payoff: string;
    unique_value_proposition: string;
  };
  campaign: {
    campaign_kpis: string;
    campaign_goals: string;
    campaign_resources: string;
    campaign_concept_timing: string;
  };
};

export type CampaignData = {
  id: number;
  step: number;
  complete: boolean;
  update_date: string;
  language: string;
  name: string;
  description: string;
  target_regions: string;
  cconcept?: CreativeConceptData | null;
  funnel?: FunnelData | null;
  channel_group?: CampaignChannelGroupData[] | null;
  big_idea?: string | null;
  timing?: string | null;
  message_location?: string | null;
  audience_experience?: string | null;
  tools?: string | null;
  product_details?: CategorySelectorAttributes | null;
  bperson_details?: CategorySelectorAttributes | null;
  campaigns?: CampaingDetailsData[] | null;
  preferred_campaign?: CampaingDetailsData | null;
  image_attributes_generated?: Partial<CreativeConceptImageAttributes> | null;
  image_attributes_saved?: CreativeConceptImageAttributes | null;
  image_prompts?: ImagePrompt[] | null;
  preferred_image_prompt?: ImagePrompt | null;
  summary_generated: SummaryCampaignData | null;
  summary_saved: SummaryCampaignData | null;
  asset_platform_project_id: string | null;
  image_url: string | null;
  thumbnail_url: string | null;
  product_image_url: string | null;
  product_thumbnail_url: string | null;
  product_name: string | null;
  bperson_image_url: string | null;
  bperson_thumbnail_url: string | null;
  bperson_name: string | null;
  ucampaign: UmbrellaCampaignData;
};

export type CampaingStyleData = {
  id: number;
  name: string;
  description: string;
  image_id: number | null;
  image_url: string | null;
  target: string;
};

export type CampaignResponse = BaseApiResponseData<CampaignData>;
export type CampaignListResponse = BaseApiPaginatedResponseData<CampaignData>;
export type CampaignSetMetricsResponse = BaseApiResponseData<
  CampaignData & {
    channel_group_metrics: {
      channel_group: number;
      metrics: CampaignChannelGroupMetric[];
    }[];
  }
>;
export type CampaingImageResponse = BaseApiResponseData<{
  id: string;
  image_url: string;
  thumbnail_url: string;
  update_date: string;
  step: number;
  name: string;
  complete: boolean;
}>;

export type CampaignAskLucaByStepResponse = BaseApiResponseData<{
  id: string;
  step: number;
  answer: string[];
}>;
export type CampaignStyleResponse = BaseApiResponseData<CampaingStyleData[]>;

export type CampaignAskLucaForOneCampaign = BaseApiResponseData<{
  id: string;
  answer: CampaingDetailsData;
}>;

export type CampaignAskLucaForCampaignList = BaseApiResponseData<{
  id: string;
  answer: CampaingDetailsData[];
}>;

export default {
  async create(
    brand_id: number,
    project_id: number,
    data: Pick<
      CampaignData,
      "name" | "description" | "target_regions" | "language"
    >,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async update(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    data: Pick<
      CampaignData,
      "name" | "description" | "target_regions" | "language"
    >,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign",
        {
          method: "PUT",
          body: {
            brand_id,
            project_id,
            campaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getOne(
    brand_id: number,
    project_id: number,
    campaign_id: number,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign/${campaign_id}`,
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getList(
    brand_id: number,
    project_id: number,
    paginationOptions: ApiDefaultPaginationOptions = {},
  ): Promise<CampaignListResponse> {
    try {
      return await $api<CampaignListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign`,
        {
          method: "GET",
          query: paginationOptionsToQuery(paginationOptions),
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setUmbrellaCampaign(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    ucampaign_id: number,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_umbrella_campaign",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            ucampaign_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setFunnelId(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    funnel_id: number,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_funnel",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            funnel_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setChannelGroups(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    channel_group: number[],
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_channel_group",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            channel_group,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setMetrics(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    data: {
      channel_group_metrics: CampaignSetMetricsResponse["data"]["channel_group_metrics"];
      advance: boolean;
    },
  ): Promise<CampaignSetMetricsResponse> {
    try {
      return await $api<CampaignSetMetricsResponse>(
        "/v2/application/hiluca/brand/project/campaign/metrics",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaByStep(
    brand_id: number,
    project_id: number,
    campaign_id: number | undefined,
    step: 5 | 6 | 7 | 8 | 9,
    text: string,
  ): Promise<CampaignAskLucaByStepResponse> {
    try {
      return await $api<CampaignAskLucaByStepResponse>(
        "/v2/application/hiluca/brand/project/campaign/ask_luca_step",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            step,
            text,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setBigIdea(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    big_idea: string,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_big_idea",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            big_idea,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setTiming(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    timing: string,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_timing",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            timing,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setMessageLocation(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    message_location: string,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_message_location",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            message_location,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setAudienceExperience(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    audience_experience: string,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_audience_experience",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            audience_experience,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setTools(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    tools: string,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_tools",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            tools,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setProductDetails(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    product_details: CategorySelectorAttributes,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_product_details",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            product_details,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setBuyerPersonDetails(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    bperson_details: CategorySelectorAttributes,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_buyer_person_details",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            bperson_details,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getImage(
    brand_id: number,
    project_id: number,
    campaign_id: number,
  ): Promise<Blob | undefined> {
    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign/${campaign_id}/image`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );
    } catch (error: any) {
      return undefined;
    }
  },

  async askLucaForOneCampaign(
    brand_id: number,
    project_id: number,
    campaign_id: number | undefined,
    data: { text: string; campaign_selected: CampaingDetailsData },
  ): Promise<CampaignAskLucaForOneCampaign> {
    try {
      return await $api<CampaignAskLucaForOneCampaign>(
        "/v2/application/hiluca/brand/project/campaign/ask_luca_campaign",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaFoCampaignList(
    brand_id: number,
    project_id: number,
    campaign_id: number | undefined,
    data: { text: string; campaigns: CampaingDetailsData[] },
  ): Promise<CampaignAskLucaForCampaignList> {
    try {
      return await $api<CampaignAskLucaForCampaignList>(
        "/v2/application/hiluca/brand/project/campaign/ask_luca_campaigns",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveGeneratedCampaigns(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    campaigns: CampaingDetailsData[],
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/generated",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            campaigns,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async SetPreferredCampaign(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    preferred_campaign_id: number,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            preferred_campaign_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getListCampaignStyleData(): Promise<CampaignStyleResponse> {
    try {
      return await $api<CampaignStyleResponse>(
        `/v2/application/hiluca/image_style?target=campaign`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async SetImageStyleByCampaign(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    image_style_id: number,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_image_style",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            image_style_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async GenerateCampaignImageAttributes(
    brand_id: number,
    project_id: number,
    campaign_id: number,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/image/attributes/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveImageAttributes(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    data: Pick<
      CampaignData,
      "image_attributes_generated" | "image_attributes_saved"
    >,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/image/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateImagePrompts(
    brand_id: number,
    project_id: number,
    campaign_id: number,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/image/prompts/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async savePreferredPrompt(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    data: ImagePrompt,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/image/prompts/preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            preferred_image_prompt: data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadImage(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    image: Blob,
  ): Promise<CampaingImageResponse> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign/${campaign_id}/image`,
        {
          method: "POST",
          body: formData,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadImageFromImgLibrary(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    image_id: string,
  ): Promise<CampaingImageResponse> {
    try {
      return await $api("/v2/application/hiluca/brand/project/campaign/image", {
        method: "POST",
        body: {
          brand_id,
          project_id,
          campaign_id,
          image_id,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async GenerateSummary(
    brand_id: number,
    project_id: number,
    campaign_id: number,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/summary/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async SaveSummary(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    data: {
      summary_generated: SummaryCampaignData;
      summary_saved: SummaryCampaignData;
    },
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/summary",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setAssetPlatformProjectId(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    asset_platform_project_id: string,
  ): Promise<CampaignResponse> {
    try {
      return await $api<CampaignResponse>(
        "/v2/application/hiluca/brand/project/campaign/set_asset_platform_project",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            asset_platform_project_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
