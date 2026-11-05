import { handleCommonErrors } from "../common-errors";
import {
  UmbrellaMotiveAndBarrier,
  UmbrellaResource,
  UmbrellaStageCategoryLCategoryData,
  UmbrellaStageCategoryListResponse,
} from "../UtilsApi";
import { CreativeConceptImageAttributes } from "./CreativeConceptsApi";

export type UmbrellaCampaignResource = UmbrellaResource & {
  text: string;
  label: string;
};

export type UmbrellaCampaignBenefit = {
  id: number;
  title: string;
  text: string;
  preferred: number;
};

export type UmbrellaCampaignEmotionalTension = {
  title: string;
  text: string;
};

export type UmbrellaCampaignDrama = {
  id: number;
  title: string;
  text: string;
  preferred: number;
};

export type UmbrellaCampaignMotiveAndBarrier = Pick<
  UmbrellaMotiveAndBarrier,
  "name" | "display_name" | "description"
> & {
  text: string;
};

export type UmbrellaCampaignDetailsSectionData = {
  text: string;
  title: string;
};

export type UmbrellaCampaignDetailsData = {
  id: number;
  title: string;
  sections: {
    hook: UmbrellaCampaignDetailsSectionData;
    message: UmbrellaCampaignDetailsSectionData;
    big_idea: UmbrellaCampaignDetailsSectionData;
  };
  preferred: number;
  description: string;
};
export type UmbrellaCampaignStage = {
  name: string;
  display_name: string;
};

export type UmbrellaCampaignStoryStage = {
  id: number;
  name: string;
  text: string;
  stage: UmbrellaCampaignStage;
  display_name: string;
};

export type UmbrellaCampaignStageSelected = UmbrellaCampaignStoryStage & {
  id: number;
};

export type UmbrellaCampaignSummarySingleAttribute = {
  id: string;
  title: string;
  content: string;
};

export type UmbrellaCampaignSummaryAttributes = {
  the_persona: UmbrellaCampaignSummarySingleAttribute[];
  the_product: UmbrellaCampaignSummarySingleAttribute[];
  the_creative_concept: UmbrellaCampaignSummarySingleAttribute[];
};

export type UmbrellaCampaignStoryStageItem = {
  id: number;
  name: string;
  display_name: string;
  text: string;
  stage: {
    name: string;
    display_name: string;
  };
};

export type UmbrellaCampaignData = {
  id: number;
  step: number;
  complete: boolean;
  update_date: string;
  name: string;
  context: string;
  language: string;
  target_regions: string;
  central_idea?: string | null;
  bperson_resources?: UmbrellaCampaignResource[] | null;
  bperson_resource_base?: UmbrellaCampaignResource | null;
  bperson_resource_exchangeable?: UmbrellaCampaignResource | null;
  resource_exchange?: {
    product_to_customer: string;
    customer_to_product: string;
  } | null;
  benefit_reasoning?: string | null;
  benefits?: UmbrellaCampaignBenefit[] | null;
  preferred_benefit?: UmbrellaCampaignBenefit | null;
  bperson_motives?: UmbrellaCampaignMotiveAndBarrier[] | null;
  bperson_barriers?: UmbrellaCampaignMotiveAndBarrier[] | null;
  bperson_motive_selected?: UmbrellaCampaignMotiveAndBarrier | null;
  bperson_barrier_selected?: UmbrellaCampaignMotiveAndBarrier | null;
  emotional_tension?: UmbrellaCampaignEmotionalTension | null;
  drama_reasoning?: string | null;
  dramas?: UmbrellaCampaignDrama[] | null;
  preferred_drama?: UmbrellaCampaignDrama | null;
  story_stages?: UmbrellaCampaignStoryStage[] | null;
  stages_selected?: UmbrellaCampaignStageSelected[] | null;
  story_plot?: string | null;
  scene_reasoning?: string | null;
  scenes?: UmbrellaCampaignBenefit[] | null;
  preferred_scene?: UmbrellaCampaignBenefit | null;
  umbrella_campaigns?: UmbrellaCampaignDetailsData[] | null;
  preferred_umbrella_campaign?: UmbrellaCampaignDetailsData | null;
  image_attributes_generated?: Partial<CreativeConceptImageAttributes> | null;
  image_attributes_saved?: CreativeConceptImageAttributes | null;
  image_prompts?: ImagePrompt2[] | null;
  preferred_image_prompt?: ImagePrompt2 | null;
  image_url?: string | null;
  thumbnail_url?: string | null;
  categories_stages?: UmbrellaStageCategoryLCategoryData[] | null;
  summary_generated: UmbrellaCampaignSummaryAttributes | null;
  summary_saved: UmbrellaCampaignSummaryAttributes | null;
  project: {
    id: number;
    name: string;
  };
  product: {
    id: number;
    name: string;
    thumbnail_url: string;
  };
  bperson: {
    id: number;
    thumbnail_url: string;
    name: string;
  };
};

export type UmbrellaCampaignResponse =
  BaseApiResponseData<UmbrellaCampaignData>;

export type UmbrellaCampaignListResponse =
  BaseApiPaginatedResponseData<UmbrellaCampaignData>;

export type UmbrellaCampaignGenerateResourceExchangeResponse =
  BaseApiResponseData<{
    id: number;
    answer: RequiredNonNullable<
      UmbrellaCampaignData,
      "resource_exchange" | "benefit_reasoning"
    >;
  }>;

export type UmbrellaCampaignGenerateBenefitsResponse = BaseApiResponseData<{
  id: number;
  answer: UmbrellaCampaignBenefit[];
}>;

export type UmbrellaCampaignGenerateSceneResponse = BaseApiResponseData<{
  id: number;
  answer: UmbrellaCampaignBenefit[];
}>;

export type UmbrellaCampaignGenerateEmotionalTensionResponse =
  BaseApiResponseData<{
    id: number;
    answer: RequiredNonNullable<
      UmbrellaCampaignData,
      "emotional_tension" | "drama_reasoning"
    >;
  }>;

export type UmbrellaCampaignGenerateDramasResponse = BaseApiResponseData<{
  id: number;
  answer: UmbrellaCampaignDrama[];
}>;

export type UmbrellaCampaingImageResponse = BaseApiResponseData<{
  id: string;
  image_url: string;
  thumbnail_url: string;
  update_date: string;
  step: number;
  name: string;
  complete: boolean;
}>;

export type UmbrellaCampaignAskLucaForBuyerResources = BaseApiResponseData<{
  id: string;
  answer: Record<
    string,
    {
      text: string;
      label: string;
    }
  >;
}>;

export type UmbrellaCampaignAskLucaForOneBuyerResource = BaseApiResponseData<{
  id: string;
  answer: Record<
    string,
    {
      text: string;
      label: string;
    }
  >;
}>;

export type UmbrellaCampaignAskLucaForBuyerPersonMotivesAndBarriers =
  BaseApiResponseData<{
    id: string;
    answer: {
      motives: Record<
        string,
        {
          text: string;
        }
      >;
      barriers: Record<
        string,
        {
          text: string;
        }
      >;
    };
  }>;

export type UmbrellaCampaignAskLucaForOneBuyerPersonMotiveAndBarrier =
  BaseApiResponseData<{
    id: string;
    answer: Record<
      string,
      {
        text: string;
      }
    >;
  }>;

export type UmbrellaCampaignAskLucaOneCampaignResponse = BaseApiResponseData<{
  id: string;
  answer: UmbrellaCampaignDetailsData;
}>;

export type UmbrellaCampaignAskLucaCampaignListResponse = BaseApiResponseData<{
  id: string;
  answer: UmbrellaCampaignDetailsData[];
}>;

export type UmbrellaCampaignAskLucaForDramasResponse = BaseApiResponseData<{
  id: string;
  answer: UmbrellaCampaignDrama[];
}>;

export type UmbrellaCampaignAskLucaForOneDramaResponse = BaseApiResponseData<{
  id: string;
  answer: UmbrellaCampaignDrama;
}>;

export type UmbrellaCampaignAskLucaForBenefitsResponse = BaseApiResponseData<{
  id: string;
  answer: UmbrellaCampaignBenefit[];
}>;

export type UmbrellaCampaignAskLucaForOneBenefitResponse = BaseApiResponseData<{
  id: string;
  answer: UmbrellaCampaignBenefit;
}>;

export type UmbrellaCampaignAskLucaScenesResponse = BaseApiResponseData<{
  id: string;
  answer: UmbrellaCampaignBenefit[];
}>;

export type UmbrelaCampaignAskLucaForaSceneResponse = BaseApiResponseData<{
  id: string;
  answer: UmbrellaCampaignBenefit;
}>;

export type StoryPlot = {
  id: string;
  answer: {
    story_plot: string;
    scene_reasoning: string;
  };
};

export type StoryPlotByUmbrellaCampaingResponse =
  BaseApiResponseData<StoryPlot>;

export default {
  async create(
    brand_id: number,
    project_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      "name" | "context" | "target_regions" | "language"
    >,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign",
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
    ucampaign_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      "name" | "context" | "target_regions" | "language"
    >,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign",
        {
          method: "PUT",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
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
    ucampaign_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/umbrella_campaign/${ucampaign_id}`,
        {
          method: "GET",
        },
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
  ): Promise<UmbrellaCampaignListResponse> {
    try {
      return await $api<UmbrellaCampaignListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/umbrella_campaign`,
        {
          method: "GET",
          query: { ...paginationOptionsToQuery(paginationOptions) },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setCentralIdea(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    central_idea: NonNullable<Required<UmbrellaCampaignData["central_idea"]>>,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/set_central_idea",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            central_idea,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setBuyerPersonResources(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    bperson_resources: NonNullable<
      Required<UmbrellaCampaignData["bperson_resources"]>
    >,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/set_bperson_resources",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            bperson_resources,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateResourceExchange(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      "bperson_resource_base" | "bperson_resource_exchangeable"
    >,
  ): Promise<UmbrellaCampaignGenerateResourceExchangeResponse> {
    try {
      return await $api<UmbrellaCampaignGenerateResourceExchangeResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generate_resource_exchange",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateBenefits(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      | "bperson_resource_base"
      | "bperson_resource_exchangeable"
      | "resource_exchange"
      | "benefit_reasoning"
    >,
  ): Promise<UmbrellaCampaignGenerateBenefitsResponse> {
    try {
      return await $api<UmbrellaCampaignGenerateBenefitsResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generate_benefits",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveGeneratedBenefits(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      | "bperson_resource_base"
      | "bperson_resource_exchangeable"
      | "resource_exchange"
      | "benefit_reasoning"
      | "benefits"
    >,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/benefit/generated",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setPreferredBenefit(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    preferred_benefit_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/benefit/set_preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            preferred_benefit_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setBuyerPersonMotivesAndBarriers(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      "bperson_motives" | "bperson_barriers"
    >,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/set_bperson_motives_barriers",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateEmotionalTension(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      "bperson_motive_selected" | "bperson_barrier_selected"
    >,
  ): Promise<UmbrellaCampaignGenerateEmotionalTensionResponse> {
    try {
      return await $api<UmbrellaCampaignGenerateEmotionalTensionResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generate_emotional_tension",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateDramas(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      | "bperson_motive_selected"
      | "bperson_barrier_selected"
      | "emotional_tension"
      | "drama_reasoning"
    >,
  ): Promise<UmbrellaCampaignGenerateDramasResponse> {
    try {
      return await $api<UmbrellaCampaignGenerateDramasResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generate_dramas",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveGeneratedDramas(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: RequiredNonNullable<
      UmbrellaCampaignData,
      | "bperson_motive_selected"
      | "bperson_barrier_selected"
      | "emotional_tension"
      | "drama_reasoning"
      | "dramas"
    >,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/drama/generated",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setPreferredDrama(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    preferred_drama_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/drama/set_preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            preferred_drama_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveGeneratedUmbrellaCampaigns(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    umbrella_campaigns: NonNullable<
      Required<UmbrellaCampaignData["umbrella_campaigns"]>
    >,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generated",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            umbrella_campaigns,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setPreferredUmbrellaCampaign(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    preferred_umbrella_campaign_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/set_preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            preferred_umbrella_campaign_id,
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
    ucampaign_id: number,
    image: Blob,
  ): Promise<UmbrellaCampaingImageResponse> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/umbrella_campaign/${ucampaign_id}/image`,
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
    ucampaign_id: number,
    image_id: string,
  ): Promise<UmbrellaCampaingImageResponse> {
    try {
      return await $api(
        "/v2/application/hiluca/brand/project/umbrella_campaign/image",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            image_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setImageStyle(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    image_style_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/set_image_style",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            image_style_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateImageAttributes(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/image/attributes/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
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
    ucampaign_id: number,
    data: Pick<
      UmbrellaCampaignData,
      "image_attributes_generated" | "image_attributes_saved"
    >,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/image/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
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
    ucampaign_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/image/prompts/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
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
    ucampaign_id: number,
    preferred_image_prompt: ImagePrompt2,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/image/prompts/preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            preferred_image_prompt,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async GenerateSummary(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/summary/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveSummary(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      summary_generated: UmbrellaCampaignSummaryAttributes;
      summary_saved: UmbrellaCampaignSummaryAttributes;
    },
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/summary",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async SettingStoryStages(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      story_stages: UmbrellaCampaignStoryStageItem[];
    },
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/scene/set_story_stages",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForBuyerResources(
    brand_id: number,
    project_id: number,
    ucampaign_id: number | undefined,
  ): Promise<UmbrellaCampaignAskLucaForBuyerResources> {
    try {
      return await $api<UmbrellaCampaignAskLucaForBuyerResources>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_buyer_resources",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForOneBuyerResource(
    brand_id: number,
    project_id: number,
    ucampaign_id: number | undefined,
    {
      bperson_resource_selected,
    }: { bperson_resource_selected: UmbrellaCampaignResource },
  ): Promise<UmbrellaCampaignAskLucaForOneBuyerResource> {
    try {
      return await $api<UmbrellaCampaignAskLucaForOneBuyerResource>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_a_buyer_resource",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            bperson_resource_selected,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForBenefits(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: { text: string } & RequiredNonNullable<
      UmbrellaCampaignData,
      | "bperson_resource_base"
      | "bperson_resource_exchangeable"
      | "resource_exchange"
      | "benefit_reasoning"
    >,
  ): Promise<UmbrellaCampaignAskLucaForBenefitsResponse> {
    try {
      return await $api<UmbrellaCampaignAskLucaForBenefitsResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_benefits",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForOneBenefit(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      text: string;
      benefit_selected: UmbrellaCampaignBenefit;
    } & RequiredNonNullable<
      UmbrellaCampaignData,
      | "bperson_resource_base"
      | "bperson_resource_exchangeable"
      | "resource_exchange"
      | "benefit_reasoning"
    >,
  ): Promise<UmbrellaCampaignAskLucaForOneBenefitResponse> {
    try {
      return await $api<UmbrellaCampaignAskLucaForOneBenefitResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_a_benefit",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForBuyerPersonMotivesAndBarriers(
    brand_id: number,
    project_id: number,
    ucampaign_id: number | undefined,
  ): Promise<UmbrellaCampaignAskLucaForBuyerPersonMotivesAndBarriers> {
    try {
      return await $api<UmbrellaCampaignAskLucaForBuyerPersonMotivesAndBarriers>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_bperson_motives_barriers",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForOneBuyerPersonMotiveAndBarrier(
    brand_id: number,
    project_id: number,
    ucampaign_id: number | undefined,
    {
      motive_barrier_selected,
    }: { motive_barrier_selected: UmbrellaCampaignMotiveAndBarrier },
  ): Promise<UmbrellaCampaignAskLucaForOneBuyerPersonMotiveAndBarrier> {
    try {
      return await $api<UmbrellaCampaignAskLucaForOneBuyerPersonMotiveAndBarrier>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_bperson_a_motive_barrier",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            motive_barrier_selected,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForDramas(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: { text: string } & RequiredNonNullable<
      UmbrellaCampaignData,
      | "bperson_motive_selected"
      | "bperson_barrier_selected"
      | "emotional_tension"
      | "drama_reasoning"
    >,
  ): Promise<UmbrellaCampaignAskLucaForDramasResponse> {
    try {
      return await $api<UmbrellaCampaignAskLucaForDramasResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_dramas",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForOneDrama(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      text: string;
      drama_selected: UmbrellaCampaignDrama;
    } & RequiredNonNullable<
      UmbrellaCampaignData,
      | "bperson_motive_selected"
      | "bperson_barrier_selected"
      | "emotional_tension"
      | "drama_reasoning"
    >,
  ): Promise<UmbrellaCampaignAskLucaForOneDramaResponse> {
    try {
      return await $api<UmbrellaCampaignAskLucaForOneDramaResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_a_drama",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForOneCampaign(
    brand_id: number,
    project_id: number,
    ucampaign_id: number | undefined,
    data: {
      text: string;
      umbrella_campaign_selected: UmbrellaCampaignDetailsData;
    },
  ): Promise<UmbrellaCampaignAskLucaOneCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignAskLucaOneCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_a_umbrella_campaign",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async askLucaForUmbrellaCampaignList(
    brand_id: number,
    project_id: number,
    ucampaign_id: number | undefined,
    data: { text: string; umbrella_campaigns: UmbrellaCampaignDetailsData[] },
  ): Promise<UmbrellaCampaignAskLucaCampaignListResponse> {
    try {
      return await $api<UmbrellaCampaignAskLucaCampaignListResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_umbrella_campaigns",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async GenerateUmbrellaStageCategoryList(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
  ): Promise<UmbrellaStageCategoryListResponse> {
    try {
      return await $api<UmbrellaStageCategoryListResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generate_categories_stages",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
          },
        },
      );
    } catch (error: any) {
      throw error;
    }
  },

  async GenerateStoryPlotByUmbrellaCampaign(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      stages_selected: UmbrellaCampaignStoryStageItem[];
    },
  ): Promise<StoryPlotByUmbrellaCampaingResponse> {
    try {
      return await $api<StoryPlotByUmbrellaCampaingResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generate_story_plot",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      throw error;
    }
  },
  async GenerateScenesByUmbrellaCampaign(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      stages_selected: UmbrellaCampaignStoryStageItem[];
      story_plot: string;
      scene_reasoning: string;
    },
  ): Promise<UmbrellaCampaignGenerateSceneResponse> {
    try {
      return await $api<UmbrellaCampaignGenerateSceneResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generate_scenes",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      throw error;
    }
  },

  async SaveGeneratedScenesBymbrellaCampaign(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      stages_selected: UmbrellaCampaignStoryStageItem[];
      story_plot: string;
      scene_reasoning: string;
      scenes: UmbrellaCampaignBenefit[];
    },
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/scene/generated",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      throw error;
    }
  },

  async SettingPreferredSceneByUmbrellaCampaign(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      preferred_scene_id: number;
    },
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/scene/set_preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      throw error;
    }
  },

  async GenerateUmbrellaCampaigns(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
  ): Promise<UmbrellaCampaignResponse> {
    try {
      return await $api<UmbrellaCampaignResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
          },
        },
      );
    } catch (error: any) {
      throw error;
    }
  },
  //**************** */

  async AskLucaForScenesByUmbrellaCampaign(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      text: string;
      stages_selected: UmbrellaCampaignStoryStageItem[];
      story_plot: string;
      scene_reasoning: string;
      scenes: UmbrellaCampaignBenefit[];
    },
  ): Promise<UmbrellaCampaignAskLucaScenesResponse> {
    try {
      return await $api<UmbrellaCampaignAskLucaScenesResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_scenes",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      throw error;
    }
  },

  async AskLucaForaSceneByUmbrellaCampaign(
    brand_id: number,
    project_id: number,
    ucampaign_id: number,
    data: {
      text: string;
      stages_selected: UmbrellaCampaignStoryStageItem[];
      story_plot: string;
      scene_reasoning: string;
      scene_selected: UmbrellaCampaignBenefit;
    },
  ): Promise<UmbrelaCampaignAskLucaForaSceneResponse> {
    try {
      return await $api<UmbrelaCampaignAskLucaForaSceneResponse>(
        "/v2/application/hiluca/brand/project/umbrella_campaign/ask_luca_a_scene",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            ucampaign_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      throw error;
    }
  },
};
