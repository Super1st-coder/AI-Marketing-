import { BuyerPersonData } from "../BuyerPersonasApi";
import { handleCommonErrors } from "../common-errors";
import { ProductData } from "../ProductsApi";
import { ProyectData } from "./ProjectsApi";

// Schema when is unlocked
export type GeneratedCreativeConceptDataV1 = {
  id: number;
  sections: {
    slogan: {
      text: string;
      title: string;
    };
    concept: {
      title: string;
      description: string;
    };
    message: {
      title: string;
      description: string;
    };

    big_idea?: undefined;
    short_description?: undefined;
  };
  preferred: 0 | 1;
  creative_concept: {
    title: string;
  };
};

// Schema when is locked
export type GeneratedCreativeConceptDataV2 = {
  id: number;
  sections: {
    slogan: {
      text: string;
      title: string;
    };
    big_idea: {
      title: string;
      description: string;
    };
    message: {
      title: string;
      description: string;
    };
    short_description: {
      title: string;
      description: string;
    };

    concept?: undefined;
  };
  preferred: 0 | 1;
  creative_concept: {
    title: string;
  };
};

// Combine the schemas into a single schema
export type GeneratedCreativeConceptData =
  | GeneratedCreativeConceptDataV1
  | GeneratedCreativeConceptDataV2;

export type CreativeConceptImageAttributes = {
  place: string;
  emotion: string;
  core_idea: string;
  primary_visual: string;
  target_audience: string;
};

export type CreativeConceptSummaryAttributes = {
  bperson: {
    story_hero: string;
    target_customer: string;
    who_reaching: string;
  };
  cconcept: {
    big_idea: string;
    message: string;
    hook: string;
  };
  product: {
    role: string;
    how_shines: string;
    solution: string;
  };
};

export type CreativeConceptData = {
  id: number;
  step: number;
  complete: boolean;
  locked: boolean;
  central_idea: string;
  matter_to_audience?: string | null;
  style?: string | null;
  platforms_and_channels?: string | null;
  creative_concepts?: GeneratedCreativeConceptData[] | null;
  preferred_creative_concept?: GeneratedCreativeConceptData | null;
  image_attributes_generated?: Partial<CreativeConceptImageAttributes> | null;
  image_attributes_saved?: CreativeConceptImageAttributes | null;
  image_prompts?: ImagePrompt[] | null;
  preferred_image_prompt?: ImagePrompt | null;
  summary_generated?: CreativeConceptSummaryAttributes | null;
  summary_saved?: CreativeConceptSummaryAttributes | null;
  project?: Pick<ProyectData, "id" | "name"> | null;
  product?: Pick<
    ProductData,
    | "id"
    | "name"
    | "description"
    | "product_story"
    | "thumbnail_url"
    | "image_url"
  > | null;
  bperson?: Pick<
    BuyerPersonData,
    "id" | "name" | "bperson_story" | "image_url" | "thumbnail_url"
  > | null;
};

export type CreativeConceptResponse = BaseApiResponseData<CreativeConceptData>;
export type CreativeConceptListResponse = BaseApiResponseData<
  CreativeConceptData[]
>;

export type CreativeConceptAskLucaByStepResponse = BaseApiResponseData<{
  id: string;
  step: number;
  answer: string[];
}>;

export default {
  async create(
    brand_id: number,
    project_id: number,
    data: Pick<CreativeConceptData, "central_idea">,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept",
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
    cconcept_id: number,
    data: Pick<CreativeConceptData, "central_idea">,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept",
        {
          method: "PUT",
          body: {
            brand_id,
            project_id,
            cconcept_id,
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
    cconcept_id: number,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/creative_concept/${cconcept_id}`,
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
  ): Promise<CreativeConceptListResponse> {
    try {
      return await $api<CreativeConceptListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/creative_concept`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setMatterToAudience(
    brand_id: number,
    project_id: number,
    cconcept_id: number,
    matter_to_audience: CreativeConceptData["matter_to_audience"],
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/set_matter_to_audience",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            matter_to_audience,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setStyle(
    brand_id: number,
    project_id: number,
    cconcept_id: number,
    style: CreativeConceptData["style"],
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/set_style",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            style,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setPlatformsAndChannel(
    brand_id: number,
    project_id: number,
    cconcept_id: number,
    platforms_and_channels: CreativeConceptData["platforms_and_channels"],
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/set_platform_channel",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            platforms_and_channels,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveGeneratedConcepts(
    brand_id: number,
    project_id: number,
    cconcept_id: number,
    creative_concepts: GeneratedCreativeConceptData[],
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/generated",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            creative_concepts,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setPreferred(
    brand_id: number,
    project_id: number,
    cconcept_id: number,
    preferred_cconcept_id: number,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/set_preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            preferred_cconcept_id,
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
    cconcept_id: number,
  ): Promise<Blob | undefined> {
    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/creative_concept/${cconcept_id}/image`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );
    } catch (error: any) {
      return undefined;
    }
  },

  async uploadImage(
    brand_id: number,
    project_id: number,
    cconcept_id: number,
    image: Blob,
  ): Promise<void> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      await $api(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}/creative_concept/${cconcept_id}/image`,
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

  async generateImageAttributes(
    brand_id: number,
    project_id: number,
    cconcept_id: number,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/image/attributes/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
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
    cconcept_id: number,
    data: Pick<
      CreativeConceptData,
      "image_attributes_generated" | "image_attributes_saved"
    >,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/image/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
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
    cconcept_id: number,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/image/prompts/generate",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setPreferredPrompt(
    brand_id: number,
    project_id: number,
    cconcept_id: number,
    image_prompt_id: number,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/image/prompts/set_preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            image_prompt_id,
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
    cconcept_id: number,
    preferred_image_prompt: ImagePrompt,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/image/prompts/preferred",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            preferred_image_prompt,
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
    cconcept_id: number | undefined,
    step: 0 | 1 | 2 | 3,
  ): Promise<CreativeConceptAskLucaByStepResponse> {
    try {
      return await $api<CreativeConceptAskLucaByStepResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/ask_luca",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            step,
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
    cconcept_id: number,
    summary_generated: CreativeConceptSummaryAttributes,
    summary_saved: CreativeConceptSummaryAttributes,
  ): Promise<CreativeConceptResponse> {
    try {
      return await $api<CreativeConceptResponse>(
        "/v2/application/hiluca/brand/project/creative_concept/summary",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            cconcept_id,
            summary_generated,
            summary_saved,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
