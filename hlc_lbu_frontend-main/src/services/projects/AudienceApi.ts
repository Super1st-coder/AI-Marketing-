import { handleCommonErrors } from "../common-errors";

export type Income =
  | "Struggling to cover basic needs."
  | "Budget-conscious, limited discretionary income."
  | "Balanced finances, occasional treats."
  | "Comfortable, prioritizes experiences and quality."
  | "High-income, enjoying premium lifestyles."
  | "Extremely wealthy with luxury preferences.";

export type Country = {
  longName: string;
  shortName: string;
  label: string;
  name: string;
  neighborhood?: string;
  state?: string;
  targetLocation: boolean;
  lat: number;
  lng: number;
};

export type AudienceItem = {
  id: number;
  name: string;
  description: string;
  age: string[];
  gender: string;
  income: Income;
  interests: string[];
  location: Country[] | string[];
  preferred: number;
  saved: boolean;
  comments?: string;
};

export type AudiencesByChannel = {
  channel_id: number;
  channel_name: string;
  preferred_audience: AudienceItem | null;
  proposal_audiences: AudienceItem[] | null;
  saved_audiences: AudienceItem[] | null;
};

export type GetAudiencesByAdSetResponse = BaseApiResponseData<{
  ad_set_id: number;
  ad_set_name: string;
  audiences: AudiencesByChannel[];
}>;

export type AiResearchSubTopic = {
  id: number;
  selected: boolean;
  name: string;
  description: string;
  sources: string[];
};

export type AiResearchTopic = {
  id: number;
  volume: number;
  engagement: number;
  sentiments: string;
  name: string;
  selected: boolean;
  subtopics: AiResearchSubTopic[];
};

export type AiResearchTopicResponse = BaseApiResponseData<AiResearchTopic[]>;

export type AiResearchTaskResponse = BaseApiResponseData<{ job_id: string }>;

export type AiResearchTaskStatus = BaseApiResponseData<{
  ready: boolean;
  successful: boolean;
  value: BaseApiResponseData<AiResearchTopic[]> | null;
}>;

export type Interest = {
  name: string;
  source: string;
};

export type Location = {
  label: string;
  target_location: boolean;
  lat: number;
  lng: number;
};

export type AudienceCreationBodyWithManualData = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  name: string;
  description: string;
  gender: string;
  age_min: number;
  age_max: number;
  income_level: Income | null;
  interests: string[];
  locations: Location[];
};

export type AudienceCreationBodyWithDescription = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  description: string;
};

export type AudienceCreationBodyWithFiles = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  files: File[];
};

export type AudienceCreationBodyWithDescriptionOrFiles =
  | AudienceCreationBodyWithDescription
  | AudienceCreationBodyWithFiles;

export type AudienceCreationBodyWithTopics = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  topics: AiResearchTopic[];
};

export type SaveUnsaveAudienceBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  channel_id: number;
  audience: AudienceItem;
};

export type DeleteAudienceBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  channel_id: number;
};

export type SetPreferredAudienceBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  channel_id: number;
  preferred_audience_id: number;
};

export type CancelProposalAudiencesBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
};

export type TopicsCreationBodyWithDescription = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  description: string;
};

export type CreateAudienceFromSavedBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  channel_id: number;
  audience: AudienceItem;
};

export type UpdatePreferredAudienceBody = {
  brand_id: number;
  campaign_id: number;
  ad_set_id: number;
  channel_id: number;
  preferred_audience: AudienceItem;
};

export default {
  async UpdatePreferredAudience(
    body: UpdatePreferredAudienceBody,
  ): Promise<BaseApiResponseData<AudiencesByChannel>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel>>(
        "v2/application/hiluca/brand/audience/preferred",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async CreateAudienceFromSaved(
    body: CreateAudienceFromSavedBody,
  ): Promise<BaseApiResponseData<AudiencesByChannel>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel>>(
        "v2/application/hiluca/brand/audience/generate/saved",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async GetSavedAudiences(
    brand_id: number,
  ): Promise<BaseApiResponseData<AudiencesByChannel[]>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel[]>>(
        `v2/application/hiluca/brand/${brand_id}/audience/saved`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async GetAudiencesByAdSet(
    brand_id: number,
    campaign_id: number,
    ad_set_id: number,
  ): Promise<GetAudiencesByAdSetResponse> {
    try {
      return await $api<GetAudiencesByAdSetResponse>(
        `v2/application/hiluca/brand/${brand_id}/campaign/${campaign_id}/ad_set/${ad_set_id}/audience`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async CancelProposalAudiences(
    body: CancelProposalAudiencesBody,
  ): Promise<{ data: [] }> {
    try {
      return await $api<{ data: [] }>(
        "v2/application/hiluca/brand/audience/cancel",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async DeleteAudience(
    body: DeleteAudienceBody,
  ): Promise<BaseApiResponseData<AudiencesByChannel>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel>>(
        "v2/application/hiluca/brand/audience/preferred/delete",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async SetPreferredAudience(
    body: SetPreferredAudienceBody,
  ): Promise<BaseApiResponseData<AudiencesByChannel>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel>>(
        "v2/application/hiluca/brand/audience/set_preferred",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async SaveAudience(
    body: SaveUnsaveAudienceBody,
  ): Promise<BaseApiResponseData<AudiencesByChannel>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel>>(
        "v2/application/hiluca/brand/audience/saved",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async UnsaveAudience(
    body: SaveUnsaveAudienceBody,
  ): Promise<BaseApiResponseData<AudiencesByChannel>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel>>(
        "v2/application/hiluca/brand/audience/unsave",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async DeleteAudienceFromSaved(
    audienceSavedId: number,
  ): Promise<BaseApiResponseData<any>> {
    try {
      return await $api<BaseApiResponseData<any>>(
        `v2/application/hiluca/brand/audience/saved/${audienceSavedId}`,
        {
          method: "DELETE",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async GenerateAudiencesWithManualData(
    body: AudienceCreationBodyWithManualData,
  ): Promise<BaseApiResponseData<AudiencesByChannel[]>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel[]>>(
        "v2/application/hiluca/brand/audience/generate/form",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateAudiencesFromDescriptionOrFile(
    body: AudienceCreationBodyWithDescriptionOrFiles,
  ): Promise<BaseApiResponseData<AudiencesByChannel[]>> {
    const formData = new FormData();

    if ("files" in body && body.files?.length) {
      Array.from(body.files).forEach((file) => {
        formData.append("files", file);
      });
    } else if ("description" in body && body.description) {
      formData.append("description", body.description);
    }

    try {
      return await $api<BaseApiResponseData<AudiencesByChannel[]>>(
        `v2/application/hiluca/brand/${body.brand_id}/campaign/${body.campaign_id}/ad_set/${body.ad_set_id}/audience/generate/description`,
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

  async generateAudiencesWithTopics(
    body: AudienceCreationBodyWithTopics,
  ): Promise<BaseApiResponseData<AudiencesByChannel[]>> {
    try {
      return await $api<BaseApiResponseData<AudiencesByChannel[]>>(
        "v2/application/hiluca/brand/audience/generate/topic",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateTopicsWithDescription(
    body: TopicsCreationBodyWithDescription,
  ): Promise<AiResearchTaskResponse> {
    try {
      return await $api<AiResearchTaskResponse>(
        "v2/application/hiluca/brand/audience/topic/generate",
        {
          body,
          method: "POST",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getTopicGenerationStatus(jobId: string): Promise<AiResearchTaskStatus> {
    try {
      return await $api<AiResearchTaskStatus>(`v2/tasks/result/${jobId}`, {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
