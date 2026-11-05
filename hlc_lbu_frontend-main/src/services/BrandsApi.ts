import {
  BaseApiPaginatedResponseData,
  BaseApiResponseData,
} from "@/utils/type-declarations";
import { handleCommonErrors } from "./common-errors";

export type BrandAttributes = {
  vision: string;
  uniqueness: string;
  story?: string;
};

export type BrandData = {
  id: number;
  name: string;
  website: string;
  vision: string | null;
  uniqueness: string | null;
  industry: string | null;
  markets: string | null;
  geography: string | null;
  attributes_generated: BrandAttributes | null;
  attributes_saved: BrandAttributes | null;
  step: number;
  complete: boolean;
  setted_voice: boolean;
  language?: string | null;
};

export type BrandResponse = BaseApiResponseData<BrandData>;
export type BrandListResponse = BaseApiPaginatedResponseData<BrandData>;
export type BrandCreateResponse = BaseApiResponseData<BrandData>;
export type BrandUpdateResponse = BaseApiResponseData<BrandData>;
export type BrandDeleteResponse = BaseApiResponseData<BrandData>;

export default {
  async getList(paginationOptions: ApiDefaultPaginationOptions = {}) {
    try {
      return await $api<BrandListResponse>(`/v2/application/hiluca/brand`, {
        method: "GET",
        query: paginationOptionsToQuery(paginationOptions),
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getOne(brand_id: number) {
    try {
      return await $api<BrandResponse>(
        `/v2/application/hiluca/brand/${brand_id}`,
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
    data: Pick<BrandData, "name" | "website">,
  ): Promise<BrandCreateResponse> {
    try {
      return await $api<BrandCreateResponse>("/v2/application/hiluca/brand", {
        method: "POST",
        body: {
          ...data,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async updateByStep(
    brand_id: number,
    data: AtLeast<Omit<BrandData, "id">, "step"> & {
      trigger_prompts?: boolean;
    },
  ): Promise<BrandUpdateResponse> {
    try {
      return await $api<BrandUpdateResponse>("/v2/application/hiluca/brand", {
        method: "PUT",
        body: {
          brand_id,
          ...data,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async update(
    brand_id: number,
    data: Omit<BrandData, "id">,
  ): Promise<BrandUpdateResponse> {
    try {
      return await $api<BrandUpdateResponse>("/v2/application/hiluca/brand", {
        method: "PUT",
        body: {
          brand_id,
          ...data,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async delete(brand_id: number): Promise<BrandDeleteResponse> {
    try {
      return await $api<BrandDeleteResponse>(
        `/v2/application/hiluca/brand/${brand_id}`,
        {
          method: "DELETE",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadImage(brand_id: number, image: Blob): Promise<void> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      await $api(`/v2/application/hiluca/brand/${brand_id}/image`, {
        method: "POST",
        body: formData,
      });
      return;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getImage(brand_id: number): Promise<Blob | undefined> {
    try {
      const response = await $api(
        `/v2/application/hiluca/brand/${brand_id}/image`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );

      return response as Blob;
    } catch (error: any) {
      return undefined;
    }
  },
};
