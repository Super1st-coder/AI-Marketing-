import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleCommonErrors } from "../../common-errors";
import { AdMediaTemplate } from "./AdsApi";

// Data structure
export type AbyssaleProject = {
  id: number;
  project_name: string;
  project_id: string;
};

// API Response types
type AbyssaleProjectResponse = BaseApiResponseData<AbyssaleProject>;
type AbyssaleProjectListResponse = BaseApiResponseData<AbyssaleProject[]>;
type AbyssaleTemplateListResponse = BaseApiResponseData<AdMediaTemplate[]>;

// Request body types
type CreateAbyssaleProjectBody = {
  brand_id: number;
  project_name: string;
  project_id: string;
};

// Errors
export class ProjectNotFoundInAbyssaleError extends Error {
  constructor() {
    super("PROJECT_NOT_FOUND_IN_ABYSSALE");
    this.name = this.constructor.name;
  }
}

export default {
  async create(
    data: CreateAbyssaleProjectBody,
  ): Promise<AbyssaleProjectResponse> {
    try {
      return await $api<AbyssaleProjectResponse>(
        "/v2/application/hiluca/brand/media_platform/project",
        {
          method: "POST",
          body: {
            ...data,
          },
        },
      );
    } catch (error: any) {
      // Check for "Project not found in Abyssale" error
      const code = error.message?.code as string | undefined;
      if (code === "DAT001") {
        throw new ProjectNotFoundInAbyssaleError();
      }

      handleCommonErrors(error);
      throw error;
    }
  },

  async getList(brandId: number): Promise<AbyssaleProjectListResponse> {
    try {
      return await $api<AbyssaleProjectListResponse>(
        `/v2/application/hiluca/brand/${brandId}/media_platform/project`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getTemplateListByProject(
    brandId: number,
    projectId: number,
  ): Promise<AbyssaleTemplateListResponse> {
    try {
      return await $api<AbyssaleTemplateListResponse>(
        `/v2/application/hiluca/brand/${brandId}/media_platform/project/${projectId}/template`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getTemplateListByAbyssaleProjectId(
    brandId: number,
    abyssaleProjectId: string,
  ): Promise<AbyssaleTemplateListResponse> {
    try {
      return await $api<AbyssaleTemplateListResponse>(
        `v2/application/hiluca/brand/${brandId}/media_platform/template/${abyssaleProjectId}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
