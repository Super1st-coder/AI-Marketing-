import { BaseApiResponseData, ImagePrompt } from "@/utils/type-declarations";
import {
  handleProjectError,
  ImageNotFoundError,
  UnidentifiedError,
} from "../common-errors";

export class MetaAdsNotFoundError extends Error {
  constructor() {
    super("META_ADS_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

export type MetaAdType = "N" | "R";

export type MetaAdData = {
  id: number;
  context: string;
  ad: {
    cta: string;
    headline: string;
    image_hook: string;
    description?: string;
    primary_text: string;
    image_punchline: string;
  };
  preferred: number;
  image_prompts?: {
    prompts: ImagePrompt[];
  };
};

export type MetaAdListResponse = BaseApiResponseData<{
  project_id: number;
  meta_ads: MetaAdData[];
}>;

export type MetaAdGeneratePromptsResponse = BaseApiResponseData<{
  project_id: number;
  meta_ad_id: number;
  target_meta_ad: MetaAdData;
  meta_ads: MetaAdData[];
}>;

export type MetaAdUploadImageResponse = BaseApiResponseData<{
  project_id: number;
  meta_ad_id: number;
  image_id: string;
  meta_ads: MetaAdData[];
}>;

export default {
  async getList(
    projectId: number | string,
    type: MetaAdType,
  ): Promise<MetaAdListResponse> {
    try {
      const response = await $api<MetaAdListResponse>(
        `/v1/application/hiluca/project/${projectId}/type/${type}/meta_ads`,
        {
          method: "GET",
        },
      );

      if (response.ok === 0) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new MetaAdsNotFoundError();
    }
  },

  async generate(
    projectId: number | string,
    type: MetaAdType,
  ): Promise<MetaAdListResponse> {
    try {
      const response = await $api<MetaAdListResponse>(
        `/v1/application/hiluca/project/meta_ads/generate`,
        {
          method: "POST",
          body: {
            project_id: projectId,
            type,
          },
        },
      );

      if (response.ok === 0) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new UnidentifiedError();
    }
  },

  async saveOne(
    projectId: number | string,
    type: MetaAdType,
    data: MetaAdData,
  ): Promise<MetaAdListResponse> {
    try {
      const response = await $api<MetaAdListResponse>(
        `/v1/application/hiluca/project/meta_ad`,
        {
          method: "POST",
          body: {
            project_id: projectId,
            type,
            meta_ad: data,
          },
        },
      );

      if (response.ok === 0) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new UnidentifiedError();
    }
  },

  async generatePrompts(
    projectId: number | string,
    type: MetaAdType,
    metaAdId: number,
  ): Promise<MetaAdGeneratePromptsResponse> {
    try {
      const response = await $api<MetaAdGeneratePromptsResponse>(
        `/v1/application/hiluca/project/meta_ad/image/prompts/generate`,
        {
          method: "POST",
          body: {
            project_id: projectId,
            type,
            meta_ad_id: metaAdId,
          },
        },
      );

      if (response.ok === 0) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new UnidentifiedError();
    }
  },

  async uploadImage(
    projectId: number | string,
    type: MetaAdType,
    metaAdId: number,
    image: Blob,
  ): Promise<MetaAdUploadImageResponse> {
    // Create a form data to append the file
    const formData = new FormData();
    formData.append("file", image);

    try {
      const response = await $api<MetaAdUploadImageResponse>(
        `/v1/application/hiluca/project/${projectId}/type/${type}/meta_ad/${metaAdId}/image`,
        {
          method: "POST",
          body: formData,
        },
      );

      if (response.ok === 0) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new UnidentifiedError();
    }
  },

  async getImage(
    projectId: number | string,
    type: MetaAdType,
    metaAdId: number,
    allowUndefined?: boolean,
  ): Promise<Blob | undefined> {
    try {
      const response = await $api(
        `/v1/application/hiluca/project/${projectId}/type/${type}/meta_ad/${metaAdId}/image`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );

      if (response.ok === 0) {
        if (allowUndefined) {
          return undefined;
        }

        throw response;
      }

      return response as Blob;
    } catch (error: any) {
      if (allowUndefined) {
        return undefined;
      }

      handleProjectError(error);

      if (error.message?.text === "ERROR - Getting Image") {
        throw new ImageNotFoundError();
      }

      throw new UnidentifiedError();
    }
  },
};
