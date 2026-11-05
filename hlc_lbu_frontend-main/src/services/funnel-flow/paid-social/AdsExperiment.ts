import { handleCommonErrors } from "../../common-errors";
import type { BaseApiResponseData } from "../../../utils/type-declarations";

export type AdsExperimentType = "static" | "ugc";

export type AdsExperimentSubcategory = {
  id: number;
  name: string;
  description: string;
  custom: boolean;
};

export type AdsExperimentCategory = {
  id: number;
  name: string;
  description: string;
  type: string;
  custom: boolean;
  subcategories: AdsExperimentSubcategory[];
};

export type AdsExperimentCategoryData = AdsExperimentCategory[];

export type AdsExperimentCategoryResponse =
  BaseApiResponseData<AdsExperimentCategoryData>;

export type AdsExperimentSubcategoriesData = {
  category_id: number;
  subcategories: AdsExperimentSubcategory[];
};

export type AdsExperimentSubcategoriesResponse =
  BaseApiResponseData<AdsExperimentSubcategoriesData>;

export type AdsExperimentCreateCategoryPayload = {
  name: string;
  description: string;
  type: string;
};

export type AdsExperimentCreateCategoryData = Omit<
  AdsExperimentCategory,
  "subcategories"
>;

export type AdsExperimentCreateCategoryResponse =
  BaseApiResponseData<AdsExperimentCreateCategoryData>;

export type AdsExperimentByAdSetData = {
  id: number;
  ad_set_id: number;
  type: AdsExperimentType;
  subcategory: {
    id: number;
    name: string;
    description: string | null;
    category: {
      id: number;
      name: string;
    };
  };
};

export type AdsExperimentByAdSetResponse =
  BaseApiResponseData<AdsExperimentByAdSetData> & {
    ok: 0 | 1;
    message?: { code: string; text: string };
  };

export default {
  async getExperimentCategories(
    brand_id: number,
    type: string,
  ): Promise<AdsExperimentCategoryResponse> {
    try {
      return await $api<AdsExperimentCategoryResponse>(
        `/v2/application/hiluca/brand/${brand_id}/ads_experiment/categories?type=${type}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getExperimentSubcategories(
    brand_id: number,
    category_id: number,
  ): Promise<AdsExperimentSubcategoriesResponse> {
    try {
      return await $api<AdsExperimentSubcategoriesResponse>(
        `/v2/application/hiluca/brand/${brand_id}/ads_experiment/category/${category_id}/subcategories`,
        { method: "GET" },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async createExperimentCategory(
    brand_id: number,
    payload: AdsExperimentCreateCategoryPayload,
  ): Promise<AdsExperimentCreateCategoryResponse> {
    try {
      return await $api<AdsExperimentCreateCategoryResponse>(
        `/v2/application/hiluca/brand/ads_experiment/category`,
        {
          method: "POST",
          body: {
            brand_id,
            ...payload,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async createExperimentSubcategory(
    brand_id: number,
    category_id: number,
    name: string,
    description: string,
  ): Promise<AdsExperimentCreateCategoryResponse> {
    try {
      return await $api<AdsExperimentCreateCategoryResponse>(
        `/v2/application/hiluca/brand/ads_experiment/category/subcategory`,
        {
          method: "POST",
          body: {
            brand_id,
            category_id,
            name,
            description,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async defineExperimentByAdSet(
    brand_id: number,
    campaign_id: number,
    ad_set_id: number,
    subcategory_id: number,
    type: AdsExperimentType,
  ): Promise<AdsExperimentByAdSetData> {
    try {
      return await $api<AdsExperimentByAdSetData>(
        `/v2/application/hiluca/brand/ads_experiment`,
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            ad_set_id,
            subcategory_id,
            type,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getExperimentByAdSet(
    brand_id: number,
    campaign_id: number,
    ad_set_id: number,
  ): Promise<AdsExperimentByAdSetResponse> {
    try {
      return await $api<AdsExperimentByAdSetResponse>(
        `/v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/ad_set/${ad_set_id}/ads_experiment`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async updateExperimentByAdSet(
    brand_id: number,
    campaign_id: number,
    experiment_id: number,
    ad_set_id: number,
    subcategory_id: number,
    type: AdsExperimentType,
  ): Promise<AdsExperimentByAdSetData> {
    try {
      return await $api<AdsExperimentByAdSetData>(
        `/v2/application/hiluca/brand/ads_experiment/${experiment_id}`,
        {
          method: "PUT",
          body: {
            brand_id,
            campaign_id,
            ad_set_id,
            subcategory_id,
            type,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async deleteExperimentByAdSet(
    brand_id: number,
    campaign_id: number,
    ad_set_id: number,
    experiment_id: number,
  ): Promise<BaseApiResponseData<undefined>> {
    try {
      return await $api<any>(
        `/v2/application/hiluca/brand/ads_experiment/${experiment_id}`,
        {
          method: "DELETE",
          body: {
            brand_id,
            campaign_id,
            ad_set_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
