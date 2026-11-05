import { BaseApiResponseData } from "@/utils/type-declarations";
import { BuyerPersonData } from "./BuyerPersonasApi";
import { handleCommonErrors } from "./common-errors";

export type BuyerPersonMainImage = {
  id: number;
  image_id: string;
  image_url: string;
  prompt: string;
  selected: boolean;
  has_variants: boolean;
};

export type BuyerPersonStartMainImageListJobBody = {
  brand_id: number;
  bperson_id: number;
  product_id: null | number;
  visual_style?: string;
};

export type BuyerPersonDeleteMainImageBody = {
  brand_id: number;
  bperson_id: number;
  main_image_id: number;
};

export type BuyerPersonStartEditMainImageJobBody = {
  brand_id: number;
  bperson_id: number;
  custom_prompt: string;
  n_variants: number;
  base_image_id?: string;
  photography_effect?: string;
  product_id?: number;
  reference_images?: File[];
  visual_style?: string;
};

export type BuyerPersonStartEditVariantJobBody = {
  brand_id: number;
  bperson_id: number;
  main_image_id: string;
  base_image_id?: string;
  custom_prompt: string;
  n_variants: number;
  photography_effect?: string;
  product_id?: number;
  reference_images?: File[];
  label?: string;
  visual_style?: string;
};

export type BuyerPersonStartGenerateCustomVariantsJobBody = {
  brand_id: number;
  bperson_id: number;
  main_image_id?: string;
  custom_prompt: string;
  n_variants: number;
  photography_effect?: string;
  product_id?: number;
  reference_images?: File[];
  visual_style?: string;
};

export type BuyerPersonSelectVariantBody = {
  brand_id: number;
  bperson_id: number;
  main_image_id: string;
  variant_image_id: string;
};

export type BuyerPersonVariantEditedImage = {
  id: number;
  image_id: string;
  image_url: string;
  label: string;
  prompt: string;
};

export type BuyerPersonVariantDetail = {
  id: number;
  image_id: string;
  image_url: string;
  label: string;
  prompt: string;
  images: BuyerPersonVariantEditedImage[];
};

export type BuyerPersonGetVariantResponse =
  BaseApiResponseData<BuyerPersonVariantDetail>;

export type BuyerPersonStartGenerateVariantsJobBody = {
  brand_id: number;
  bperson_id: number;
  image_id: string;
  labels?: string[] | null;
};

export type BuyerPersonUploadMainImageBinaryBody = {
  brand_id: number;
  bperson_id: number;
  file: File;
};

export type BuyerPersonUploadMainImageByIdBody = {
  brand_id: number;
  bperson_id: number;
  image_id: string;
};

export type BuyerPersonSelectMainImageBody = {
  brand_id: number;
  bperson_id: number;
  image_id: string;
};

export type BuyerPersonCompleteImagesBody = {
  brand_id: number;
  bperson_id: number;
};

export type BuyerPersonCompleteImagesResponse =
  BaseApiResponseData<BuyerPersonData>;

export type BuyerPersonMainImageResponse =
  BaseApiResponseData<BuyerPersonMainImage>;

export type BuyerPersonDeleteVariantBody = {
  brand_id: number;
  bperson_id: number;
  base_image_id: string;
  variant_id: number;
};

export type BuyerPersonUploadVariantBinaryBody = {
  brand_id: number;
  bperson_id: number;
  base_image_id: string;
  file: File;
  label?: string;
};

export type BuyerPersonUploadVariantByIdBody = {
  brand_id: number;
  bperson_id: number;
  base_image_id: string;
  image_id: string;
  label?: string;
};

export type BuyerPersonStartMainImageListJobResponse = BaseApiResponseData<{
  job_id: string;
}>;

export type BuyerPersonMainImageListResponse = BaseApiResponseData<{
  id: number;
  main_images: BuyerPersonMainImage[];
}>;

export type BuyerPersonMainImageVariant = {
  id: number;
  image_id: string;
  image_url: string;
  label: string;
  prompt: string;
  status: "A" | "I" | "P";
};

export type BuyerPersonMainImageVariantsResponse = BaseApiResponseData<{
  id: number;
  base_image_id: string;
  variants: BuyerPersonMainImageVariant[];
}>;

export type BuyerPersonDeleteVariantResponse = BaseApiResponseData<
  Omit<BuyerPersonMainImageVariant, "image_url">
>;

export type BuyerPersonUploadVariantResponse =
  BaseApiResponseData<BuyerPersonMainImageVariant>;

export type BuyerPersonMainImageListJobResultProgress = {
  task_id: string;
  status: "PROGRESS";
  meta: {
    step: string;
  };
};

export type BuyerPersonMainImageListJobResultSuccess = {
  task_id: string;
  status: "DONE";
  result: "Ok";
};

export type GenerateAdVariationsJobResultRetry = {
  task_id: string;
  status: "RETRY";
  meta: {
    raw: string;
  };
};

export type BuyerPersonMainImageListJobResultFailed = {
  task_id: string;
  status: "FAILED";
  error: string;
  traceback: string | null;
};

export type BuyerPersonMainImageListJobResult = BaseApiResponseData<
  | BuyerPersonMainImageListJobResultProgress
  | BuyerPersonMainImageListJobResultSuccess
  | GenerateAdVariationsJobResultRetry
  | BuyerPersonMainImageListJobResultFailed
>;

export default {
  async getMainImageList(brand_id: number, buyer_person_id: number) {
    try {
      const response = await $api<BuyerPersonMainImageListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/buyer_person/${buyer_person_id}/image/main`,
        {
          method: "GET",
        },
      );

      // Sort array by IDs
      const sorted: BuyerPersonMainImageListResponse = {
        ...response,
        data: {
          ...response.data,
          main_images: [...response.data.main_images].sort(
            (a, b) => a.id - b.id,
          ),
        },
      };

      return sorted;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async startGenerateMainImageListJob(
    data: BuyerPersonStartMainImageListJobBody,
  ) {
    try {
      return await $api<BuyerPersonStartMainImageListJobResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/automatic/main/generate",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getGenerateMainImageListJobResult(jobId: string) {
    try {
      return await $api<BuyerPersonMainImageListJobResult>(
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

  async deleteMainImage(data: BuyerPersonDeleteMainImageBody) {
    try {
      return await $api<BuyerPersonMainImageListJobResult>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/main/${data.main_image_id}`,
        {
          method: "DELETE",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getMainImageVariants(
    brand_id: number,
    bperson_id: number,
    base_image_id: string,
    options?: { unlabeled?: boolean },
  ) {
    try {
      return await $api<BuyerPersonMainImageVariantsResponse>(
        `/v2/application/hiluca/brand/${brand_id}/buyer_person/${bperson_id}/image/main/${base_image_id}/variants`,
        {
          method: "GET",
          query: {
            ...(options?.unlabeled ? { unlabeled: true } : {}),
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async deleteVariant(data: BuyerPersonDeleteVariantBody) {
    try {
      return await $api<BuyerPersonDeleteVariantResponse>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/main/${data.base_image_id}/variant/${data.variant_id}`,
        {
          method: "DELETE",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async startGenerateVariantsJob(
    data: BuyerPersonStartGenerateVariantsJobBody,
  ) {
    try {
      return await $api<BuyerPersonStartMainImageListJobResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/variant/generate",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadMainImageBinary(data: BuyerPersonUploadMainImageBinaryBody) {
    const formData = new FormData();
    formData.append("file", data.file);

    try {
      return await $api<BuyerPersonMainImageResponse>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/main`,
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

  async uploadMainImageById(data: BuyerPersonUploadMainImageByIdBody) {
    try {
      return await $api<BuyerPersonMainImageResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/main",
        {
          method: "POST",
          body: {
            brand_id: data.brand_id,
            bperson_id: data.bperson_id,
            image_id: data.image_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async selectMainImage(data: BuyerPersonSelectMainImageBody) {
    try {
      return await $api<BuyerPersonMainImageResponse>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/main/${data.image_id}/select`,
        {
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async completeImages(data: BuyerPersonCompleteImagesBody) {
    try {
      return await $api<BuyerPersonCompleteImagesResponse>(
        "/v2/application/hiluca/brand/buyer_person/image/complete",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadVariantBinary(data: BuyerPersonUploadVariantBinaryBody) {
    const formData = new FormData();
    formData.append("file", data.file);

    if (data.label) {
      formData.append("label", data.label);
    }

    try {
      return await $api<BuyerPersonUploadVariantResponse>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/main/${data.base_image_id}/variant`,
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

  async uploadVariantById(data: BuyerPersonUploadVariantByIdBody) {
    try {
      return await $api<BuyerPersonUploadVariantResponse>(
        `/v2/application/hiluca/brand/buyer_person/image/main/${data.base_image_id}/variant`,
        {
          method: "POST",
          body: {
            brand_id: data.brand_id,
            bperson_id: data.bperson_id,
            image_id: data.image_id,
            ...(data.label ? { label: data.label } : {}),
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async startEditMainImageJob(data: BuyerPersonStartEditMainImageJobBody) {
    const formData = new FormData();
    formData.append("custom_prompt", data.custom_prompt);
    formData.append("n_variants", String(data.n_variants));

    if (data.base_image_id) {
      formData.append("base_image_id", data.base_image_id);
    }

    if (data.photography_effect) {
      formData.append("photography_effect", data.photography_effect);
    }

    if (data.product_id) {
      formData.append("product_id", String(data.product_id));
    }

    if (data.reference_images?.length) {
      data.reference_images.forEach((file) => {
        formData.append("reference_images", file);
      });
    }

    if (data.visual_style) {
      formData.append("visual_style", data.visual_style);
    }

    try {
      return await $api<BuyerPersonStartMainImageListJobResponse>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/main/edit`,
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

  async startEditVariantJob(data: BuyerPersonStartEditVariantJobBody) {
    const formData = new FormData();
    formData.append("custom_prompt", data.custom_prompt);
    formData.append("n_variants", String(data.n_variants));

    if (data.base_image_id) {
      formData.append("base_image_id", data.base_image_id);
    }

    if (data.photography_effect) {
      formData.append("photography_effect", data.photography_effect);
    }

    if (data.product_id) {
      formData.append("product_id", String(data.product_id));
    }

    if (data.reference_images?.length) {
      data.reference_images.forEach((file) => {
        formData.append("reference_images", file);
      });
    }

    if (data.label) {
      formData.append("label", data.label);
    }

    if (data.visual_style) {
      formData.append("visual_style", data.visual_style);
    }

    try {
      return await $api<BuyerPersonStartMainImageListJobResponse>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/main/${data.main_image_id}/variant/edit`,
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

  async startGenerateCustomVariantsJob(
    data: BuyerPersonStartGenerateCustomVariantsJobBody,
  ) {
    const formData = new FormData();
    formData.append("custom_prompt", data.custom_prompt);
    formData.append("n_variants", String(data.n_variants));

    if (data.main_image_id) {
      formData.append("main_image_id", data.main_image_id);
    }

    if (data.photography_effect) {
      formData.append("photography_effect", data.photography_effect);
    }

    if (data.product_id) {
      formData.append("product_id", String(data.product_id));
    }

    if (data.reference_images?.length) {
      data.reference_images.forEach((file) => {
        formData.append("reference_images", file);
      });
    }

    if (data.visual_style) {
      formData.append("visual_style", data.visual_style);
    }

    try {
      return await $api<BuyerPersonStartMainImageListJobResponse>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/variant/custom/generate`,
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

  async getVariant(brand_id: number, bperson_id: number, image_id: string) {
    try {
      return await $api<BuyerPersonGetVariantResponse>(
        `/v2/application/hiluca/brand/${brand_id}/buyer_person/${bperson_id}/image/variant/${image_id}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async selectVariant(data: BuyerPersonSelectVariantBody) {
    try {
      return await $api<BaseApiResponseData<unknown>>(
        `/v2/application/hiluca/brand/${data.brand_id}/buyer_person/${data.bperson_id}/image/main/${data.main_image_id}/variant/${data.variant_image_id}/select`,
        {
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
