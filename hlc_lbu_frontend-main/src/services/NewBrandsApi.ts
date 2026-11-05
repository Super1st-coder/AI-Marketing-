import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleCommonErrors } from "./common-errors";

// Source types for brand data
export type BrandSourceType = "pdf" | "website";

export type BrandSource = {
  page: string | null;
  type: BrandSourceType | null;
  value: string | null;
};

// Identity field structure
export type IdentityField<T = string> = {
  value: T;
  source: BrandSource[];
};

// Brand identity structure
export type BrandIdentity = {
  about_us?: IdentityField<string>;
  mission?: IdentityField<string>;
  vision?: IdentityField<string>;
  values?: IdentityField<string[]>;
  tone_voice?: IdentityField<string[]>;
};

export const brandFormLogoCategories = [
  "main-logo",
  "logotype",
  "isotype",
  "vertical-lockup",
  "horizontal-lockup",
  "monochrome",
  "negative",
  "favicon",
  "custom",
] as const;

export type BrandFormLogoCategory = (typeof brandFormLogoCategories)[number];

// Logo structure
export type BrandLogo = {
  id: number;
  image_id: string | null;
  image_url: string | null;
  category: BrandFormLogoCategory;
  description: string;
  source: BrandSource[];
  category_alias: string | null;
};

export const brandFormColorCategories = [
  "primary",
  "secondary",
  "accent",
  "neutral",
] as const;

export type BrandFormColorCategory = (typeof brandFormColorCategories)[number];

// Color structure
export type BrandColor = {
  id: number;
  name: string;
  hex_code: string;
  category: BrandFormColorCategory;
  source: BrandSource[];
};

export const brandFormTypographyStyles = [
  "thin",
  "extra-light",
  "light",
  "regular",
  "medium",
  "semi-bold",
  "bold",
  "extra-bold",
  "black",
  "italic",
] as const;

export type BrandFormTypographyStyle =
  (typeof brandFormTypographyStyles)[number];

export const brandFormTypographyUsages = [
  "display",
  "headings",
  "subheadings",
  "body",
  "captions",
  "buttons",
  "accents",
] as const;

export type BrandFormTypographyUsage =
  (typeof brandFormTypographyUsages)[number];

export const brandFormRuleTypes = ["do", "dont"] as const;

export type BrandFormRuleType = (typeof brandFormRuleTypes)[number];

// Font structure
export type BrandFont = {
  id: number;
  style: BrandFormTypographyStyle;
  usage: BrandFormTypographyUsage;
  file: string | null;
  file_id: string | null;
};

// Typography structure
export type BrandTypography = {
  id: number;
  family: string;
  fonts: BrandFont[];
};

// Dos and Don'ts structure
export type BrandDosDont = {
  id: number;
  type: BrandFormRuleType;
  rule: string;
  image_id: string | null;
  image_url: string | null;
  source: BrandSource[];
};

export type BrandResponseCollection<T> = {
  values: T[];
  complete: boolean;
};

// Full brand data structure
export type BrandData = {
  id: number;
  name: string;
  creation_method: "MANUAL" | "AI";
  complete: boolean;
  // website_url could come as an empty string ""
  website_url?: string | "" | null;
  language?: string | null;
  identity: BrandIdentity & { complete: boolean };
  logos: BrandResponseCollection<BrandLogo> | BrandLogo[];
  colors: BrandResponseCollection<BrandColor> | BrandColor[];
  typography: BrandResponseCollection<BrandTypography> | BrandTypography[];
  dos_donts: BrandDosDont[];
};

export type BrandDataSourceWebsite = {
  id: number;
  name: string;
  type: "URL";
  presigned_url: null;
};

export type BrandDataDoc = {
  id: number;
  name: string;
  type: "DOC";
  presigned_url: string;
};

export type BrandDataSource = BrandDataSourceWebsite | BrandDataDoc;

// API Response types
export type BrandResponse = BaseApiResponseData<BrandData>;

export type BrandListResponse = BaseApiResponseData<BrandData[]> & {
  count: number;
  total: number;
};

export type BrandDataSourceListResponse = BaseApiResponseData<{
  id: number;
  name: string;
  data_sources: BrandDataSource[];
}>;

export type ResearchOnlineResponse = BaseApiResponseData<{
  attribute: string;
  text: string;
}>;

export type BrandUploadLogoResponse = BaseApiResponseData<{
  image_id: string;
  image_url: string;
}>;

export type BrandUploadFontResponse = BaseApiResponseData<{
  file: string;
  file_id: string;
}>;

export type BrandDeleteResponse = BaseApiResponseData<BrandData>;

export type UploadDataSourceResponse = BaseApiResponseData<BrandData>;

export type DeleteDataSourceResponse = BaseApiResponseData<BrandData>;

// Request body types
export type CreateBrandManualBody = {
  name: string;
  website_url: string;
  language: string;
};

export type CreateBrandByAIBody = {
  name: string;
  website_url: string;
  language: string;
  files: File[];
  urls: string[];
};

export type UpdateBrandBody = {
  identity?: BrandIdentity;
  logos?: BrandLogo[];
  colors?: BrandColor[];
  typography?: BrandTypography[];
  dos_donts?: BrandDosDont[];
};

export type BrandIdentityAttribute =
  "about_us" | "mission" | "vision" | "values" | "tone_voice";

export type ResearchOnlineBody = {
  brand_id: number;
  attribute: BrandIdentityAttribute;
};

export type GenerateIdentityWithAIBody = {
  brand_id: number;
  attribute: BrandIdentityAttribute;
};

export type UploadDataSourceBody = {
  brand_id: number;
  urls: string[];
  files: File[];
  section: "all" | "logos" | "colors" | "typography" | "dos_donts";
};

export type EditBrandDataSourceDeletion = {
  data_source_id: number;
  data_source_name: string;
};

export type EditBrandBody = {
  brand_id: number;
  name: string;
  website_url: string;
  language: string;
  files: File[];
  urls: string[];
  analyze: boolean;
  delete_data_sources?: EditBrandDataSourceDeletion[];
};

export type DeleteDataSourceBody = {
  brand_id: number;
  data_source_id: number;
  data_source_name: string;
};

export class BrandAlreadyExistsError extends Error {
  constructor() {
    super("BRAND_ALREADY_EXISTS");
    this.name = this.constructor.name;
  }
}

/**
 * The company already has as many brands as licenses (Credits V1, Gate 3: 1 license = 1 brand;
 * credits never unlock more brands). The backend answers BRAND001; the user is sent to their
 * Account Manager.
 */
export class BrandLimitReachedError extends Error {
  constructor() {
    super("BRAND_LIMIT_REACHED");
    this.name = this.constructor.name;
  }
}

export default {
  async create(data: CreateBrandManualBody): Promise<BrandResponse> {
    try {
      return await $api<BrandResponse>(
        "/v2/application/hiluca/new_brand/manual",
        {
          method: "POST",
          body: {
            name: data.name,
            website_url: data.website_url,
            language: data.language,
          },
        },
      );
    } catch (error: any) {
      // Check for brand already exists error
      const code = error.message?.code ?? (error?.code as string | undefined);
      const message =
        error.message?.text ?? (error?.message as string | undefined);

      if (code === "BRAND001") {
        throw new BrandLimitReachedError();
      }

      if (
        code === "BRAND00" ||
        code === "DAT003" ||
        message === "ERROR - Brand name already exists" ||
        message === "Brand name already exists"
      ) {
        throw new BrandAlreadyExistsError();
      }

      handleCommonErrors(error);
      throw error;
    }
  },

  async createByAI(data: CreateBrandByAIBody): Promise<BrandResponse> {
    const formData = new FormData();
    formData.append("name", data.name);
    formData.append("website_url", data.website_url);
    formData.append("language", data.language);

    // Add files
    data.files.forEach((file) => {
      formData.append("files", file);
    });

    // Add URLs
    if (data.urls) {
      formData.append("urls", JSON.stringify(data.urls));
    }

    try {
      return await $api<BrandResponse>("/v2/application/hiluca/new_brand/ai", {
        method: "POST",
        body: formData,
      });
    } catch (error: any) {
      // Check for brand already exists error
      const code = error.message?.code ?? (error?.code as string | undefined);
      const message =
        error.message?.text ?? (error?.message as string | undefined);

      if (code === "BRAND001") {
        throw new BrandLimitReachedError();
      }

      if (
        code === "BRAND00" ||
        code === "DAT003" ||
        message === "ERROR - Brand name already exists" ||
        message === "Brand name already exists"
      ) {
        throw new BrandAlreadyExistsError();
      }

      handleCommonErrors(error);
      throw error;
    }
  },

  async update(brandId: number, data: UpdateBrandBody): Promise<BrandResponse> {
    try {
      return await $api<BrandResponse>(
        `/v2/application/hiluca/new_brand/${brandId}`,
        {
          method: "PUT",
          body: {
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getList(
    paginationOptions: ApiDefaultPaginationOptions = {},
  ): Promise<BrandListResponse> {
    try {
      return await $api<BrandListResponse>("/v2/application/hiluca/new_brand", {
        method: "GET",
        query: paginationOptionsToQuery(paginationOptions),
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getById(brandId: number): Promise<BrandResponse> {
    try {
      return await $api<BrandResponse>(
        `/v2/application/hiluca/new_brand/${brandId}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async researchOnline(
    data: ResearchOnlineBody,
  ): Promise<ResearchOnlineResponse> {
    try {
      return await $api<ResearchOnlineResponse>(
        "/v2/application/hiluca/new_brand/research_online",
        {
          method: "POST",
          body: {
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateIdentityWithAI(
    data: GenerateIdentityWithAIBody,
  ): Promise<ResearchOnlineResponse> {
    try {
      return await $api<ResearchOnlineResponse>(
        "/v2/application/hiluca/new_brand/generate_ai",
        {
          method: "POST",
          body: {
            ...data,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadBrandLogo(
    brand_id: number,
    image: Blob,
  ): Promise<BrandUploadLogoResponse> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      return await $api<BrandUploadLogoResponse>(
        `/v2/application/hiluca/new_brand/${brand_id}/logo/1/image`,
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

  async uploadDoDontImage(
    brand_id: number,
    image: Blob,
  ): Promise<BrandUploadLogoResponse> {
    const formData = new FormData();
    formData.append("file", image);

    try {
      return await $api<BrandUploadLogoResponse>(
        `/v2/application/hiluca/new_brand/${brand_id}/do_dont/1/image`,
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

  async uploadFontFile(
    brand_id: number,
    file: Blob,
  ): Promise<BrandUploadFontResponse> {
    const formData = new FormData();
    formData.append("file", file);

    try {
      return await $api<BrandUploadFontResponse>(
        `/v2/application/hiluca/new_brand/${brand_id}/font/1/file`,
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

  async delete(brandId: number): Promise<BrandDeleteResponse> {
    try {
      return await $api<BrandDeleteResponse>(
        `/v2/application/hiluca/new_brand/${brandId}`,
        {
          method: "DELETE",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getDataSourceList(
    brandId: number,
  ): Promise<BrandDataSourceListResponse> {
    try {
      return await $api<BrandDataSourceListResponse>(
        `/v2/application/hiluca/new_brand/data_source/${brandId}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async editBrand(data: EditBrandBody): Promise<BrandResponse> {
    const formData = new FormData();
    formData.append("name", data.name);
    formData.append("website_url", data.website_url);
    formData.append("language", data.language);
    formData.append("analyze", String(data.analyze));

    data.files.forEach((file) => {
      formData.append("files", file);
    });

    formData.append("urls", JSON.stringify(data.urls));

    if (data.delete_data_sources?.length) {
      formData.append(
        "delete_data_sources",
        JSON.stringify(data.delete_data_sources),
      );
    }

    try {
      return await $api<BrandResponse>(
        `/v2/application/hiluca/new_brand/edit/${data.brand_id}`,
        {
          method: "PUT",
          body: formData,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async uploadDataSource(
    data: UploadDataSourceBody,
  ): Promise<UploadDataSourceResponse> {
    const formData = new FormData();

    data.files.forEach((file) => {
      formData.append("files", file);
    });

    formData.append("urls", JSON.stringify(data.urls));

    formData.append("section", data.section);

    try {
      return await $api<UploadDataSourceResponse>(
        `/v2/application/hiluca/new_brand/data_source/${data.brand_id}`,
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

  async deleteDataSource(
    data: DeleteDataSourceBody,
  ): Promise<DeleteDataSourceResponse> {
    try {
      return await $api<DeleteDataSourceResponse>(
        "/v2/application/hiluca/new_brand/data_source/remove",
        {
          method: "POST",
          body: {
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
