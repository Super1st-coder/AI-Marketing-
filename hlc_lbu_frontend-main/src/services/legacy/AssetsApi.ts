import { handleCommonErrors } from "../common-errors";
import { CreativeConceptImageAttributes } from "../projects/CreativeConceptsApi";

export type AssetSimpleTemplate = {
  template_id: string;
  template_name: string;
  template_preview_url: string;
  generated: boolean;
  saved: boolean;
};

export type AssetTemplateFormat = {
  id: string;
  width: number;
  height: number;
  unit: string;
  preview_url: string;
  errors?: string[];
};

export type AssetTemplateElement = {
  name: string;
  type: string;
  payload: string | null;
  intention: string | null;
  // This was added on
  original_payload?: string;
};

export type AssetTemplateImage = {
  name: string;
  type: string;
  image_id?: string | null;
  preview_url: string;
  image_style_id?: number | null;
  image_attributes_generated?: Partial<CreativeConceptImageAttributes> | null;
  image_attributes_saved?: CreativeConceptImageAttributes | null;
  image_prompts?: ImagePrompt[] | null;
  preferred_image_prompt?: ImagePrompt | null;
};

export type AssetTemplate = {
  template_id: string;
  template_name: string;
  tone?: string | null;
  language?: string | null;
  extra_context?: string | null;
  generated: boolean;
  saved: boolean;
  formats: AssetTemplateFormat[];
  elements: AssetTemplateElement[];
  images: AssetTemplateImage[];
  generation_request_pending: boolean;
};

export type AssetSimpleTemplateListResponse = BaseApiResponseData<
  AssetSimpleTemplate[]
>;

export type AssetTemplateResponse = BaseApiResponseData<AssetTemplate>;

export type AssetGeneratedTextsResponse = BaseApiResponseData<
  AssetTemplateElement[]
>;

export type AssetGeneratedTextResponse =
  BaseApiResponseData<AssetTemplateElement>;

export type AssetDelivery = {
  campaign_name: string;
  type: string;
  summary: {
    bperson: {
      title?: string | null;
      image_url?: string | null;
      persona_journey: string;
      persona_profile: string;
      persona_challenges: string;
      persona_motivation: string;
    };
    product: {
      title?: string | null;
      image_url?: string | null;
      core_incentive_offer: string;
      problem_solution_fit: string;
      emotional_outcome_payoff: string;
      unique_value_proposition: string;
    };
    campaign: {
      title?: string | null;
      image_url?: string | null;
      campaign_kpis: string;
      campaign_goals: string;
      campaign_resources: string;
      campaign_concept_timing: string;
    };
  };
  masters: {
    id: number;
    title: string;
    images: [
      {
        horizontal: string | null;
      },
      {
        square: string | null;
      },
      {
        vertical: string | null;
      },
    ];
  }[];
};

export type AssetDeliveryResponse = BaseApiResponseData<AssetDelivery>;

export default {
  async getTemplateList(
    brand_id: number,
    project_id: number,
    campaign_id: number,
  ): Promise<AssetSimpleTemplateListResponse> {
    try {
      return await $api<AssetSimpleTemplateListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign/${campaign_id}/marketing_asset/templates`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getOneTemplate(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
  ): Promise<AssetTemplateResponse> {
    try {
      return await $api<AssetTemplateResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign/${campaign_id}/marketing_asset/template/${template_id}`,
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveTemplate(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    data: Pick<
      AssetTemplate,
      "tone" | "extra_context" | "elements" | "language"
    > & {
      generate_visual: boolean;
    },
  ): Promise<AssetTemplateResponse> {
    try {
      return await $api<AssetTemplateResponse>(
        "/v2/application/hiluca/brand/project/campaign/marketing_asset",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            template_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateTexts(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    data: Pick<
      AssetTemplate,
      "tone" | "extra_context" | "elements" | "language"
    >,
  ): Promise<AssetGeneratedTextsResponse> {
    try {
      return await $api<AssetGeneratedTextsResponse>(
        "/v2/application/hiluca/brand/project/campaign/marketing_asset/generate_texts",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            template_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateText(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    data: Pick<AssetTemplate, "tone" | "extra_context" | "language"> & {
      element: AssetTemplateElement;
    },
  ): Promise<AssetGeneratedTextResponse> {
    try {
      return await $api<AssetGeneratedTextResponse>(
        "/v2/application/hiluca/brand/project/campaign/marketing_asset/generate_text",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            template_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getTemplateImage(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    image_name: string,
  ): Promise<Blob | undefined> {
    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign/${campaign_id}/marketing_asset/${template_id}/image/${image_name}`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );
    } catch (error: any) {
      return undefined;
    }
  },

  async uploadTemplateImage(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    image_name: string,
    image: Blob,
  ): Promise<void> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      await $api(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign/${campaign_id}/marketing_asset/${template_id}/image/${image_name}`,
        {
          method: "POST",
          body: formData,
        },
      );
      return;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setTemplateImageStyle(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    image_name: string,
    image_style_id: number,
  ): Promise<AssetTemplateResponse> {
    try {
      return await $api<AssetTemplateResponse>(
        "/v2/application/hiluca/brand/project/campaign/marketing_asset/set_image_style",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            template_id,
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

  async generateTemplateImageAttributes(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    image_name: string,
    data: Pick<
      AssetTemplate,
      "tone" | "extra_context" | "elements" | "language"
    >,
  ): Promise<AssetTemplateResponse> {
    try {
      return await $api<AssetTemplateResponse>(
        "/v2/application/hiluca/brand/project/campaign/marketing_asset/image/attributes/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            template_id,
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

  async saveTemplateImageAttributes(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    image_name: string,
    data: Pick<
      AssetTemplateImage,
      "image_attributes_generated" | "image_attributes_saved"
    >,
  ): Promise<AssetTemplateResponse> {
    try {
      return await $api<AssetTemplateResponse>(
        "/v2/application/hiluca/brand/project/campaign/marketing_asset/image/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            template_id,
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

  async generateTemplateImagePrompts(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    image_name: string,
    data: Pick<
      AssetTemplate,
      "tone" | "extra_context" | "elements" | "language"
    >,
  ): Promise<AssetTemplateResponse> {
    try {
      return await $api<AssetTemplateResponse>(
        "/v2/application/hiluca/brand/project/campaign/marketing_asset/image/prompts/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            template_id,
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

  async saveTemplateImagePreferredPrompt(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    template_id: string,
    image_name: string,
    data: ImagePrompt,
  ): Promise<AssetTemplateResponse> {
    try {
      return await $api<AssetTemplateResponse>(
        "/v2/application/hiluca/brand/project/campaign/marketing_asset/image/prompts/preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            campaign_id,
            template_id,
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

  async getAssetDelivery(
    brand_id: number,
    project_id: number,
    campaign_id: number,
  ): Promise<AssetDeliveryResponse> {
    try {
      return await $api<AssetDeliveryResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/campaign/${campaign_id}/asset_delivery`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveAssetDelivery(
    brand_id: number,
    project_id: number,
    campaign_id: number,
    data: AssetDelivery,
  ): Promise<AssetDeliveryResponse> {
    try {
      return await $api<AssetDeliveryResponse>(
        "/v2/application/hiluca/brand/project/campaign/asset_delivery",
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
};
