import {
  BaseApiResponseData,
  RefinerAttributes,
} from "@/utils/type-declarations";
import { handleCommonErrors } from "./common-errors";

export type ProductImage = {
  url: string;
  thumbnail_id: string;
};

export type ProductData = {
  id: number;
  name: string;
  update_date: string;
  product_url?: string | null;
  description?: string | null;
  mandatory_attributes_generated?: RefinerAttributes | null;
  mandatory_attributes_saved?: RefinerAttributes | null;
  optional_attributes_generated?: RefinerAttributes | null;
  optional_attributes_saved?: RefinerAttributes | null;
  product_story?: string | null;
  locked: boolean;
  step: number;
  complete: boolean;
  language?: string | null;
  image_url?: string | null;
  thumbnail_url?: string | null;
  images?: ProductImage[] | null;
};

export type ProductResponse = BaseApiResponseData<ProductData>;
export type ProductListResponse = BaseApiPaginatedResponseData<ProductData>;
export type ProductCreateResponse = BaseApiResponseData<ProductData>;
export type ProductUpdateResponse = BaseApiResponseData<ProductData>;
export type ProductDeleteResponse = BaseApiResponseData<ProductData>;
export type ProductGenerateAttributesResponse =
  BaseApiResponseData<ProductData>;
export type ProductGenerateAttributesByCategoryResponse = BaseApiResponseData<{
  category: string;
  attributes_generated: RefinerAttributes;
}>;

export type ProductUploadImageResponse = BaseApiResponseData<{
  thumbnail_url: string;
}>;

export default {
  async create(
    brand_id: number | string,
    data: Pick<ProductData, "name" | "product_url" | "description">,
  ): Promise<ProductCreateResponse> {
    try {
      return await $api<ProductCreateResponse>(
        "/v2/application/hiluca/brand/product",
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
    product_id: number,
    data: Partial<Pick<ProductData, "name" | "product_url" | "description">>,
  ): Promise<ProductUpdateResponse> {
    console.log("uipdate");
    try {
      return await $api<ProductUpdateResponse>(
        "/v2/application/hiluca/brand/product",
        {
          method: "PUT",
          body: {
            brand_id,
            product_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async completeProduct(
    brand_id: number,
    product_id: number,
    product_story: string,
  ): Promise<ProductUpdateResponse> {
    try {
      return await $api<ProductUpdateResponse>(
        "/v2/application/hiluca/brand/product/complete",
        {
          method: "POST",
          body: {
            brand_id,
            product_id,
            product_story,
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
    product_id: number | string,
  ): Promise<ProductResponse> {
    try {
      return await $api<ProductResponse>(
        `/v2/application/hiluca/brand/${brand_id}/product/${product_id}`,
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
    {
      onlyComplete,
      ...paginationOptions
    }: { onlyComplete?: boolean } & ApiDefaultPaginationOptions = {},
  ) {
    try {
      return await $api<ProductListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/product`,
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

  async uploadImage(
    brand_id: number,
    product_id: number,
    image: Blob,
  ): Promise<ProductUploadImageResponse> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      const response = await $api(
        `/v2/application/hiluca/brand/${brand_id}/product/${product_id}/image`,
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
    product_id: number,
    image_id: string,
  ): Promise<ProductUploadImageResponse> {
    const body = {
      brand_id,
      product_id,
      image_id,
    };

    try {
      const response = await $api(
        `/v2/application/hiluca/brand/product/image`,
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

  async deleteImage(
    brand_id: number,
    product_id: number,
    thumbnail_id: string,
  ): Promise<BaseApiResponse> {
    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/product/${product_id}/image/${thumbnail_id}`,
        {
          method: "DELETE",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadFiles(
    brand_id: number,
    product_id: number,
    files: File[],
  ): Promise<BaseApiResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/product/${product_id}/document`,
        {
          method: "POST",
          body: formData,
        },
      );
    } catch (error: any) {
      return error;
      //handleCommonErrors(error);
      //throw error;
    }
  },

  async getImage(
    brand_id: number,
    product_id: number,
  ): Promise<Blob | undefined> {
    try {
      return await $api(
        `/v2/application/hiluca/brand/${brand_id}/product/${product_id}/image`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );
    } catch (error: any) {
      return undefined;
    }
  },

  async generateAttributes(
    brand_id: number | string,
    product_id: number | string,
    data: { trigger_prompts?: boolean } = {},
  ): Promise<ProductGenerateAttributesResponse> {
    try {
      return await $api<ProductGenerateAttributesResponse>(
        "/v2/application/hiluca/brand/product/attributes/generate",
        {
          method: "POST",
          body: {
            brand_id,
            product_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async saveAttributes(
    brand_id: number | string,
    product_id: number | string,
    data: Pick<
      ProductData,
      | "mandatory_attributes_generated"
      | "mandatory_attributes_saved"
      | "optional_attributes_generated"
      | "optional_attributes_saved"
    > & {
      not_advance?: boolean;
      trigger_prompts?: boolean;
    },
  ): Promise<ProductGenerateAttributesResponse> {
    try {
      return await $api<ProductGenerateAttributesResponse>(
        "/v2/application/hiluca/brand/product/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            product_id,
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateAttributesByCategory(
    brand_id: number | string,
    product_id: number | string,
    data: {
      category: string;
      ask: string;
      answer: string;
    },
  ): Promise<ProductGenerateAttributesByCategoryResponse> {
    try {
      return await $api<ProductGenerateAttributesByCategoryResponse>(
        "/v2/application/hiluca/brand/product/category/attributes",
        {
          method: "POST",
          body: {
            brand_id,
            product_id,
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
