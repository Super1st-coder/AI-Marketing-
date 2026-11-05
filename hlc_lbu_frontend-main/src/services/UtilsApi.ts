export type VoiceToTextResponse = BaseApiResponseData<{
  text: string;
}>;

export type FunnelData = {
  id: number;
  name: string;
  description: string;
  active: boolean;
};

export type FunnelListResponse = BaseApiResponseData<FunnelData[]>;

export type ChannelGroupData = {
  id: number;
  name: string;
  description: string;
  type: string;
  active: boolean;
};
export type ChannelGroupListResponse = BaseApiResponseData<ChannelGroupData[]>;

// This needs to be updated when the metric groups are updated in the backend
export const metricGroups = ["Goals", "Resources", "Marketing"] as const;
export type MetricGroup = (typeof metricGroups)[number];

// This needs to be updated when the metric types are updated in the backend
export const metricTypes = ["number"] as const;
export type MetricType = (typeof metricTypes)[number];

export type MetricData = {
  id: number;
  name: string;
  display_name: string;
  unit: string | null;
  value: string;
  type: MetricType;
  target: string;
  group: MetricGroup;
};
export type MetricListResponse = BaseApiResponseData<MetricData[]>;

export type UmbrellaResource = {
  name: string;
  display_name: string;
  description: string;
};
export type UmbrellaResourceListResponse = BaseApiResponseData<
  UmbrellaResource[]
>;

export type UmbrellaMotiveAndBarrier = {
  id: number;
  name: string;
  display_name: string;
  description: string;
};
export type UmbrellaMotiveAndBarrierListResponse = BaseApiResponseData<{
  motives: UmbrellaMotiveAndBarrier[];
  barriers: UmbrellaMotiveAndBarrier[];
}>;

export type StageData = {
  name: string;
  display_name: string;
  text: string;
};

export type UmbrellaStageCategoryLCategoryData = {
  name: string;
  display_name: string;
  stages: StageData[];
};

export type UmbrellaStageCategoryListResponse = BaseApiResponseData<
  UmbrellaStageCategoryLCategoryData[]
>;

export type TaskResult<T = unknown> = BaseApiResponseData<{
  ready: boolean;
  successful: boolean;
  value: T | null;
}>;

export type TaskStartResponse = BaseApiResponseData<{
  job_id: string;
}>;

export class VoiceToTextError extends Error {
  constructor() {
    super("VoiceToTextError");
    this.name = this.constructor.name;
  }
}

export default {
  async voiceToText(
    audioBlob: Blob,
    language: string,
  ): Promise<VoiceToTextResponse> {
    const formData = new FormData();
    formData.append("file", audioBlob);
    formData.append("language", language);

    try {
      return await $api<VoiceToTextResponse>(
        `/v2/application/hiluca/convert/voice/to/text`,
        {
          method: "POST",
          body: formData,
        },
      );
    } catch (error: any) {
      throw new VoiceToTextError();
    }
  },

  async getFunnelList(): Promise<FunnelListResponse> {
    try {
      return await $api(`/v2/application/hiluca/funnel`);
    } catch (error: any) {
      throw error;
    }
  },

  async getChannelGroupList(): Promise<ChannelGroupListResponse> {
    try {
      return await $api(`/v2/application/hiluca/channel_group`);
    } catch (error: any) {
      throw error;
    }
  },

  async getMetricList(group?: string): Promise<MetricListResponse> {
    try {
      return await $api(`/v2/application/hiluca/metric`, {
        query: { group },
      });
    } catch (error: any) {
      throw error;
    }
  },

  async getUmbrellaResourceList(): Promise<UmbrellaResourceListResponse> {
    try {
      return await $api(`/v2/application/hiluca/umbrella_resource`);
    } catch (error: any) {
      throw error;
    }
  },

  async getUmbrellaMotiveAndBarrierList(): Promise<UmbrellaMotiveAndBarrierListResponse> {
    try {
      return await $api(`/v2/application/hiluca/umbrella_motive_barrier`);
    } catch (error: any) {
      throw error;
    }
  },

  async getUmbrellaStageCategoryList(): Promise<UmbrellaStageCategoryListResponse> {
    try {
      return await $api(`/v2/application/hiluca/umbrella_stage_category`);
    } catch (error: any) {
      throw error;
    }
  },

  async getTaskResult<T = unknown>(jobId: string): Promise<TaskResult<T>> {
    return await $api<TaskResult<T>>(`v2/tasks/result/${jobId}`, {
      method: "GET",
    });
  },

  async getBinaryFromPresignedUrl(presignedUrl: string): Promise<Blob> {
    return await $api(`/v2/application/hiluca/binary_object`, {
      method: "GET",
      query: { presigned_url: presignedUrl },
      responseType: "blob",
    });
  },
};
