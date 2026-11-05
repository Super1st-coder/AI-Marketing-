import { handleCommonErrors } from "../../common-errors";

export type DownloadExcelParams = {
  date_to?: string;
  date_from?: string;
  status?: string;
  project_id: number;
  campaign_id: number;
  brand_id: number;
};

export type UploadExcelBody = {
  brand_id: string;
  object_type: string;
  validation_rules: null;
};

export type DownloadExcelBulkBody = {
  brand_id: number;
  campaign_id: number;
  project_id: number;
  status: string;
  date_from: string;
  date_to: string;
};

export default {
  async DownloadExcel(params: DownloadExcelParams): Promise<any> {
    try {
      return await $api<any>(
        `/v2/application/hiluca/brand/${params.brand_id}/ads/export_excel`,
        {
          method: "GET",
          query: {
            campaigns: [params.campaign_id],
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async UploadExcel(file: File, params): Promise<any> {
    try {
      const formData = new FormData();
      formData.append("file", file);

      return await $api<any>(
        `/v2/application/hiluca/brand/${params.brand_id}/campaign/${params.campaign_id}/ads/import_excel`,
        {
          method: "POST",
          body: formData,
          headers: {},
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async DownloadExcelBulk(body: DownloadExcelBulkBody): Promise<any> {
    try {
      return await $api<any>("/v2/external/excel/export/bulk", {
        method: "POST",
        body,
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
