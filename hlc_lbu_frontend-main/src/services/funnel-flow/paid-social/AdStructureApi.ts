import { handleCommonErrors } from "../../common-errors";
import { groupChannelStyles } from "../../../constants/campaigns";
import { CampaignChannelGroupData } from "../../projects/CampaignsApi";
import { TaskStartResponse } from "../../UtilsApi";

export type AdData = {
  id: number;
  name: string;
};

export type AdSetData = {
  id: number;
  name: string;
  description?: string | null;
  media_platform_project_id?: number | null;
  ads: AdData[];
};

export type GetChannelGroupListResponse = BaseApiResponseData<{
  campaign_id: number;
  campaign_update_date: string;
  channel_group: CampaignChannelGroupData[];
}>;

export type DefineAdStructureResponse = BaseApiResponseData<{
  id: number;
  campaign_id: number;
  channel_group: number;
  ad_sets: AdSetData[];
}>;

export type GenerateAdVariationsJobBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  n_variants: number;
};

export type GenerateAdVariationsJobResultPending = {
  task_id: string;
  status: "PENDING";
  meta: unknown;
};

export type GenerateAdVariationsJobResultProgress = {
  task_id: string;
  status: "PROGRESS";
  meta: {
    step: string;
  };
};

export type GenerateAdVariationsJobResultSuccess = {
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

export type GenerateAdVariationsJobResultFailed = {
  task_id: string;
  status: "FAILED";
  error: string;
  traceback: string;
};

export type GenerateAdVariationsJobResultData =
  | GenerateAdVariationsJobResultPending
  | GenerateAdVariationsJobResultProgress
  | GenerateAdVariationsJobResultSuccess
  | GenerateAdVariationsJobResultRetry
  | GenerateAdVariationsJobResultFailed;

export type GenerateAdVariationsJobResult =
  BaseApiResponseData<GenerateAdVariationsJobResultData>;

export function isGenerateAdVariationsJobFinished(
  result: GenerateAdVariationsJobResultData,
): boolean {
  return result.status === "DONE" || result.status === "FAILED";
}

export class FunnelFlowNotFoundError extends Error {
  constructor() {
    super("FUNNEL_FLOW_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

export default {
  async getChannelGroupList(
    brand_id: number,
    campaign_id: number,
  ): Promise<GetChannelGroupListResponse> {
    try {
      const data = await $api<GetChannelGroupListResponse>(
        `/v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/ad_structure/channel_group`,
        {
          method: "GET",
        },
      );

      // Sort list
      data.data.channel_group = data.data.channel_group.sort((a, b) => {
        const availableA =
          groupChannelStyles[a.name]?.availableInFunnelFlow ?? false;
        const availableB =
          groupChannelStyles[b.name]?.availableInFunnelFlow ?? false;

        if (availableA && !availableB) return -1;
        if (!availableA && availableB) return 1;

        return 0;
      });

      return data;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getAdStructureByChannelGroup(
    brand_id: number,
    campaign_id: number,
    channel_group: number,
  ): Promise<DefineAdStructureResponse> {
    try {
      return await $api<DefineAdStructureResponse>(
        `/v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/channel_group/${channel_group}/ad_structure`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      const message = error.message?.text;

      handleCommonErrors(error);

      if (message === "ERROR - Funnel Flow Not Found")
        throw new FunnelFlowNotFoundError();

      throw error;
    }
  },

  async defineAdStructure(
    brand_id: number,
    campaign_id: number,
    channel_group: number,
    {
      ad_number,
      ad_set_number,
    }: {
      ad_set_number: number;
      ad_number: number;
    },
  ): Promise<DefineAdStructureResponse> {
    try {
      return await $api<DefineAdStructureResponse>(
        "/v2/application/hiluca/brand/ad_structure",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            channel_group,
            ad_set_number,
            ad_number,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async addAdToAdSet(
    brand_id: number,
    campaign_id: number,
    channel_group: number,
    ad_structure_id: number,
    ad_set_id: number,
    ad_name: string,
  ): Promise<
    BaseApiResponseData<{ id: number; ad_name: string; ad_set_id: number }>
  > {
    try {
      return await $api<
        BaseApiResponseData<{ id: number; ad_name: string; ad_set_id: number }>
      >(`/v2/application/hiluca/brand/ad_structure/ad_set/ad`, {
        method: "POST",
        body: {
          brand_id,
          campaign_id,
          channel_group,
          ad_structure_id,
          ad_set_id,
          ad_name: ad_name,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async deleteAd(
    brand_id: number,
    campaign_id: number,
    channel_group: number,
    ad_structure_id: number,
    ad_set_id: number,
    ad_id: number,
  ): Promise<BaseApiResponseData<[]>> {
    try {
      return await $api<BaseApiResponseData<[]>>(
        "/v2/application/hiluca/brand/ad_structure/ad_set/delete_ad",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            channel_group,
            ad_structure_id,
            ad_set_id,
            ad_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async deleteAdSet(
    brand_id: number,
    campaign_id: number,
    channel_group: number,
    ad_structure_id: number,
    ad_set_id: number,
  ): Promise<BaseApiResponseData<[]>> {
    try {
      return await $api<BaseApiResponseData<[]>>(
        "/v2/application/hiluca/brand/ad_structure/delete_ad_set",
        {
          method: "POST",
          body: {
            brand_id,
            campaign_id,
            channel_group,
            ad_structure_id,
            ad_set_id,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async addAdSet(
    brand_id: number,
    campaign_id: number,
    channel_group: number,
    ad_structure_id: number,
    ad_set_name: string,
  ): Promise<
    BaseApiResponseData<{
      id: number;
      ad_set_name: string;
      ad_structure_id: number;
    }>
  > {
    try {
      return await $api<
        BaseApiResponseData<{
          id: number;
          ad_set_name: string;
          ad_structure_id: number;
        }>
      >("/v2/application/hiluca/brand/ad_structure/ad_set", {
        method: "POST",
        body: {
          brand_id,
          campaign_id,
          channel_group,
          ad_structure_id,
          ad_set_name,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async updateAdStructure(
    brand_id: number,
    campaign_id: number,
    channel_group: number,
    ad_structure_id: number,
    ad_sets: { id: number; name: string }[],
  ): Promise<DefineAdStructureResponse> {
    try {
      return await $api<DefineAdStructureResponse>(
        "/v2/application/hiluca/brand/ad_structure",
        {
          method: "PUT",
          body: {
            brand_id,
            campaign_id,
            channel_group,
            ad_structure_id,
            ad_sets,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async SetAbbysaleProjectToAdSet(data: {
    brand_id: number;
    campaign_id: number;
    ad_set_id: number;
    media_platform_project_id: number | null;
  }): Promise<
    BaseApiResponseData<{ id: number; ad_name: string; ad_set_id: number }>
  > {
    try {
      return await $api<
        BaseApiResponseData<{ id: number; ad_name: string; ad_set_id: number }>
      >(`/v2/application/hiluca/brand/ad_set/media_platform/project`, {
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

  async startGenerateAdVariationsJob(data: GenerateAdVariationsJobBody) {
    try {
      return await $api<TaskStartResponse>(
        "/v2/application/hiluca/brand/ad_set/variants",
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

  async getGenerateAdVariationsJobResult(
    jobId: string,
    options?: { signal?: AbortSignal },
  ) {
    try {
      return await $api<GenerateAdVariationsJobResult>(
        `/v2/application/hiluca/brand/ad_set/variants/job/${jobId}`,
        {
          method: "GET",
          // Pass through the signal when provided so callers can abort
          signal: options?.signal,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
