import { BaseApiResponseData, ImagePrompt } from "@/utils/type-declarations";
import { handleCommonErrors } from "./common-errors";
import { ProductData } from "./ProductsApi";

export type AttributeItem = {
  id: string;
  idx: number;
};

/**
 * Representa cada objeto en el arreglo principal `mandatory_attributes_groups`.
 */
export type MandatoryAttributeGroup = {
  id: string;
  idx: number;
  items: AttributeItem[];
  display_name: string;
};

export type BuyerPersonImageAttributes = {
  objects_or_props: string;
  activity_or_action: string;
  physical_appearance: string;
  background: string;
  expression_and_emotion: string;
};

export type BuyerPersonData = {
  id: number;
  name: string;
  update_date: string;
  description_01: string;
  description_02: string;
  description_03: string;
  mandatory_attributes_generated?: RefinerAttributes | null;
  mandatory_attributes_saved?: RefinerAttributes | null;
  complete: boolean;
  step: number;
  locked: boolean;
  bperson_story?: string | null;
  product?: Pick<ProductData, "id" | "name" | "description"> | null;
  image_attributes_generated?: Partial<BuyerPersonImageAttributes> | null;
  image_attributes_saved?: BuyerPersonImageAttributes | null;
  image_prompts?: ImagePrompt[] | null;
  preferred_image_prompt?: ImagePrompt | null;
  language?: string | null;
  image_url?: string | null;
  thumbnail_url?: string | null;
  mandatory_attributes_groups: MandatoryAttributeGroup[];
};

export type BuyerPersonResponse = BaseApiResponseData<BuyerPersonData>;
export type BuyerPersonListResponse =
  BaseApiPaginatedResponseData<BuyerPersonData>;
export type BuyerPersonCreateResponse = BaseApiResponseData<BuyerPersonData>;
export type BuyerPersonUpdateResponse = BaseApiResponseData<BuyerPersonData>;
export type BuyerPersonSetProductResponse = BaseApiResponseData<
  BuyerPersonData & { product_id: number | null }
>;
export type BuyerPersonGenerateAttributesResponse =
  BaseApiResponseData<BuyerPersonData>;

export type BuyerPersonAttributesByCategoryResponse = BaseApiResponseData<{
  category: string;
  attributes_generated: RefinerAttributes;
}>;

export type BuyerPersonGenerateImageAttributesResponse =
  BaseApiResponseData<BuyerPersonData>;
export type BuyerPersonGenerateImagePromptsResponse =
  BaseApiResponseData<BuyerPersonData>;
export type BuyerPersonSetPreferredImagePromptsResponse =
  BaseApiResponseData<BuyerPersonData>;

export type BuyerPersonUploadImageResponse = BaseApiResponseData<{
  thumbnail_url: string;
}>;

export default {
  async getList(
    brand_id: number,
    {
      onlyComplete,
      ...paginationOptions
    }: {
      onlyComplete?: boolean;
    } & ApiDefaultPaginationOptions = {},
  ) {
    try {
      return await $api<BuyerPersonListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/buyer_person`,
        {
          method: "GET",
          query: {
            onlyComplete,
            ...paginationOptionsToQuery(paginationOptions),
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
    bperson_id: number | string,
  ): Promise<BuyerPersonResponse> {
    try {
      return await $api<BuyerPersonResponse>(
        `/v2/application/hiluca/brand/${brand_id}/buyer_person/${bperson_id}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async create(
    brand_id: number | string,
    data: {
      description_01: string;
      description_02: string;
      description_03: string;
    },
  ): Promise<BuyerPersonCreateResponse> {
    try {
      return await $api<BuyerPersonCreateResponse>(
        "/v2/application/hiluca/brand/buyer_person",
        {
          method: "POST",
          body: {
            brand_id,
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
    bperson_id: number,
    data: Partial<
      Pick<
        BuyerPersonData,
        | "name"
        | "description_01"
        | "description_02"
        | "description_03"
        | "language"
      >
    >,
  ): Promise<BuyerPersonUpdateResponse> {
    try {
      return await $api<BuyerPersonUpdateResponse>(
        "/v2/application/hiluca/brand/buyer_person",
        {
          method: "PUT",
          body: {
            brand_id,
            bperson_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setProduct(
    brand_id: number,
    bperson_id: number,
    product_id: number | null,
  ): Promise<BuyerPersonSetProductResponse> {
    try {
      return await $api<BuyerPersonSetProductResponse>(
        "/v2/application/hiluca/brand/buyer_person/set_product",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
            product_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadFiles(
    brand_id: number,
    bperson_id: number,
    files: File[],
  ): Promise<BaseApiResponse> {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/buyer_person/${bperson_id}/document`,
        {
          method: "POST",
          body: formData,
        },
      );
    } catch (error: any) {
      //console.error("Error uploading files:", error);
      return error;
    }
  },

  async generateAttributes(
    brand_id: number | string,
    bperson_id: number | string,
    trigger_prompts?: boolean,
  ): Promise<BuyerPersonGenerateAttributesResponse> {
    try {
      return await $api<BuyerPersonGenerateAttributesResponse>(
        "/v2/application/hiluca/brand/buyer_person/attributes/generate",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
            trigger_prompts:
              trigger_prompts === undefined ? true : trigger_prompts,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveAttributes(
    brand_id: number,
    bperson_id: number,
    data: Pick<
      BuyerPersonData,
      "mandatory_attributes_generated" | "mandatory_attributes_saved"
    > & {
      trigger_prompts?: boolean;
    },
  ): Promise<BuyerPersonGenerateAttributesResponse> {
    try {
      return await $api<BuyerPersonGenerateAttributesResponse>(
        "/v2/application/hiluca/brand/buyer_person/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id: bperson_id.toString(),
            ...data,
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
    bperson_id: number,
  ): Promise<Blob | undefined> {
    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/buyer_person/${bperson_id}/image`,
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
    bperson_id: number,
    image: Blob,
  ): Promise<BuyerPersonUploadImageResponse> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      const response = await $api(
        `/v2/application/hiluca/brand/${brand_id}/buyer_person/${bperson_id}/image`,
        {
          method: "POST",
          body: formData,
        },
      );

      return response;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadImageFromImgLibrary(
    brand_id: number,
    bperson_id: number,
    image_id: string,
  ): Promise<BuyerPersonUploadImageResponse> {
    const body = {
      brand_id,
      bperson_id,
      image_id,
    };

    try {
      const response = await $api(
        `/v2/application/hiluca/brand/buyer_person/image`,
        {
          method: "POST",
          body,
        },
      );

      return response;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateAttributesByCategory(
    brand_id: number | string,
    bperson_id: number | string,
    data: {
      category: string;
      ask: string;
      answer: string;
      description: string;
    },
  ): Promise<BuyerPersonAttributesByCategoryResponse> {
    try {
      return await $api<BuyerPersonAttributesByCategoryResponse>(
        "/v2/application/hiluca/brand/buyer_person/category/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
            ...data,
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
    bperson_id: number,
    data: { trigger_prompts?: boolean } = {},
  ): Promise<BuyerPersonGenerateImageAttributesResponse> {
    try {
      return await $api<BuyerPersonGenerateImageAttributesResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/attributes/generate",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
            ...data,
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
    bperson_id: number,
    data: Pick<
      BuyerPersonData,
      "image_attributes_generated" | "image_attributes_saved"
    >,
  ): Promise<BuyerPersonGenerateImageAttributesResponse> {
    try {
      return await $api<BuyerPersonGenerateImageAttributesResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
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
    bperson_id: number,
  ): Promise<BuyerPersonGenerateImagePromptsResponse> {
    try {
      return await $api<BuyerPersonGenerateImagePromptsResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/prompts/generate",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
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
    bperson_id: number,
    image_prompt_id: number,
  ): Promise<BuyerPersonSetPreferredImagePromptsResponse> {
    try {
      return await $api<BuyerPersonSetPreferredImagePromptsResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/prompts/set_preferred",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
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
    bperson_id: number,
    preferred_image_prompt: ImagePrompt,
  ): Promise<BuyerPersonSetPreferredImagePromptsResponse> {
    try {
      return await $api<BuyerPersonSetPreferredImagePromptsResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/prompts/preferred",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
            preferred_image_prompt,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async completeBuyerPerson(
    brand_id: number,
    bperson_id: number,
    bperson_story: string,
    name_and_nickname: string,
  ): Promise<BuyerPersonUpdateResponse> {
    try {
      return await $api<BuyerPersonUpdateResponse>(
        "/v2/application/hiluca/brand/buyer_person/complete",
        {
          method: "POST",
          body: {
            brand_id,
            bperson_id,
            bperson_story,
            name_and_nickname,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
