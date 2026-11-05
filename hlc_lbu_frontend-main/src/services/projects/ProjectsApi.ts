import {
  BaseApiResponseData,
  RefinerAttributes,
} from "@/utils/type-declarations";
import { handleCommonErrors } from "../common-errors";
import { BuyerPersonData } from "../BuyerPersonasApi";
import { ProductData } from "../ProductsApi";

export type ProjectAttributes = {
  facing_the_challenge: string;
  struggling_to_find_solution: string;
  discovering_new_possibilities: string;
};

export type ProyectData = {
  id: number;
  name: string;
  product_name: string;
  update_date: string;
  description: string;
  language: string;
  step: number;
  status: "P" | "A";
  target_regions: string;
  summary_generated: ProjectAttributes | null;
  summary_saved: ProjectAttributes | null;
  main_goal: string | null;
  product?: Pick<
    ProductData,
    | "id"
    | "name"
    | "description"
    | "product_story"
    | "thumbnail_url"
    | "image_url"
  > | null;
  bperson?:
    | (Pick<
        BuyerPersonData,
        | "id"
        | "name"
        | "bperson_story"
        | "description_01"
        | "description_02"
        | "description_03"
        | "thumbnail_url"
        | "image_url"
      > & { customer_goal?: string[] | null })
    | null;
};

export type ProductCreateResponse = BaseApiResponseData<
  ProyectData & { product_attributes_generated: RefinerAttributes }
>;

export type ProjectCreateResponse = BaseApiResponseData<ProyectData>;
export type ProjectUpdateResponse = BaseApiResponseData<ProyectData>;

export type ProjectResponse = BaseApiResponseData<ProyectData>;

export type ProjectListResponse = BaseApiPaginatedResponseData<ProyectData>;

export type ProjectSetProductResponse = BaseApiResponseData<ProyectData>;

export default {
  async create(
    brand_id: number,
    data: Pick<
      ProyectData,
      "name" | "language" | "description" | "target_regions"
    >,
  ): Promise<ProjectCreateResponse> {
    try {
      return await $api<ProjectCreateResponse>(
        "/v2/application/hiluca/brand/project",
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
    project_id: number,
    data: Partial<
      Pick<ProyectData, "name" | "language" | "description" | "target_regions">
    >,
  ): Promise<ProjectUpdateResponse> {
    try {
      return await $api<ProjectUpdateResponse>(
        "/v2/application/hiluca/brand/project",
        {
          method: "PUT",
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

  async getOne(brand_id: number, project_id: number): Promise<ProjectResponse> {
    try {
      return await $api<ProjectResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project/${project_id}`,
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
    paginationOptions: ApiDefaultPaginationOptions = {},
  ) {
    try {
      return await $api<ProjectListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/project`,
        {
          method: "GET",
          query: paginationOptionsToQuery(paginationOptions),
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setProduct(
    brand_id: number,
    project_id: number,
    product_id: number,
  ): Promise<ProjectCreateResponse> {
    try {
      return await $api<ProjectCreateResponse>(
        "/v2/application/hiluca/brand/project/set_product",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            product_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async setBuyerPerson(
    brand_id: number,
    project_id: number,
    bperson_id: number,
    options: {
      trigger_prompts?: boolean;
    },
  ): Promise<ProjectCreateResponse> {
    try {
      return await $api<ProjectCreateResponse>(
        "/v2/application/hiluca/brand/project/set_buyer_person",
        {
          method: "POST",
          body: {
            brand_id,
            project_id,
            bperson_id,
            ...options,
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
    data: {
      summary_generated: ProjectAttributes | null;
      summary_saved: ProjectAttributes;
      main_goal: string | null;
    },
  ): Promise<ProjectCreateResponse> {
    try {
      return await $api<ProjectCreateResponse>(
        "/v2/application/hiluca/brand/project/summary",
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
};
