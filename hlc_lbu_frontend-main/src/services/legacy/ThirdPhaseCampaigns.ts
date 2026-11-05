import { BaseApiResponseData, ImagePrompt } from "@/utils/type-declarations";
import { $api } from "../../utils/api";
import { CampaignConcept } from "@/components/legacy/ad-generation/third-phase/cards/CampaignConceptCard.vue";

//campañas
export type CampaignData = {
  id: number;
  campaign: {
    title: string;
  };
  sections: {
    slogan: {
      text: string;
      title: string;
    };
    concept: {
      title: string;
      description: string;
    };
    message: {
      title: string;
      description: string;
    };
  };
  preferred: number;
};

export type CampaignListResponse = BaseApiResponseData<{
  project_id: number;
  campaigns: CampaignData[];
}>;

export type PreferredCampaignResponse = BaseApiResponseData<{
  project_id: number;
  preferred_campaign: CampaignData;
}>;

export type CampaignPromptListResponse = BaseApiResponseData<{
  project_id: number;
  campaign_image_prompts: ImagePrompt[];
}>;

export type CampaignSelectedPromptResponse = BaseApiResponseData<{
  project_id: number;
  campaign_image_prompt_id: number;
  selected_campaign_image_prompt: ImagePrompt;
}>;

export default {
  mapDataToSchema(campaignData: CampaignData): CampaignConcept {
    return {
      id: campaignData.id,
      selected: campaignData.preferred === 1,
      title: campaignData.campaign.title,
      description: campaignData.campaign.title,
      concept: campaignData.sections.concept.description,
      message: campaignData.sections.message.description,
      slogan: campaignData.sections.slogan.text,
    };
  },

  mapSchemaToData(creativeConcept: CampaignConcept): CampaignData {
    return {
      id: creativeConcept.id,
      campaign: {
        title: creativeConcept.title,
      },
      sections: {
        slogan: {
          text: creativeConcept.slogan,
          title: "Slogan",
        },
        concept: {
          title: "Concept",
          description: creativeConcept.concept,
        },
        message: {
          title: "Message",
          description: creativeConcept.message,
        },
      },
      preferred: creativeConcept.selected ? 1 : 0,
    };
  },

  //Generate Campaigns
  // servicio 6/17 de la fase 3 :  Select a creative concept you’d prefer to test
  async generate(project_id: number): Promise<CampaignListResponse> {
    try {
      const response = await $api<CampaignListResponse>(
        "/v1/application/hiluca/project/campaign/generate",
        {
          method: "POST",
          body: {
            project_id,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to Generate Campaigns");
    }
  },

  //Setting Preferred Campaign
  // servicio 7/17 de la fase 3 :  Select a creative concept you’d prefer to test
  async setPreferred(
    project_id: number,
    campaign_id: number,
  ): Promise<PreferredCampaignResponse> {
    try {
      const response = await $api<PreferredCampaignResponse>(
        "/v1/application/hiluca/project/campaign/set_preferred",
        {
          method: "POST",
          body: {
            project_id,
            campaign_id,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to Setting Preferred Campaign");
    }
  },

  //Save Preferred Campaign
  // servicio 11/17 de la fase 3 :  Select a creative concept you’d prefer to test
  async savePreferred(
    project_id: number,
    preferred_campaign: CampaignData,
  ): Promise<CampaignListResponse> {
    try {
      const response = await $api<CampaignListResponse>(
        "/v1/application/hiluca/project/preferred_campaign",
        {
          method: "POST",
          body: {
            project_id,
            preferred_campaign,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to Save Preferred Campaign");
    }
  },

  //Generate Image Prompts from Preferred Campaign
  // servicio 8/17 de la fase 3 :  Select a creative concept you’d prefer to test
  async generatePrompts(
    project_id: number,
  ): Promise<CampaignPromptListResponse> {
    try {
      const response = await $api<CampaignPromptListResponse>(
        "/v1/application/hiluca/project/preferred_campaign/image/prompts/generate",
        {
          method: "POST",
          body: {
            project_id,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error(
        "Failed to Generate Image Prompts from Preferred Campaign",
      );
    }
  },

  //Setting Preferred Image Prompt from Preferred Campaign
  // servicio 9/17 de la fase 3 :  Select a creative concept you’d prefer to test
  async setPreferredPrompt(
    project_id: number,
    campaign_image_prompt_id: number,
  ): Promise<CampaignSelectedPromptResponse> {
    try {
      const response = await $api<CampaignSelectedPromptResponse>(
        "/v1/application/hiluca/project/preferred_campaign/image/prompts/set_preferred",
        {
          method: "POST",
          body: {
            project_id,
            campaign_image_prompt_id,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error(
        "Failed to Setting Preferred Image Prompt from Preferred Campaign",
      );
    }
  },

  // Upload Campaign Image
  // servicio 10/17 de la fase 3 :  Select a creative concept you’d prefer to test
  async uploadImage(project_id: number, image: File | Blob): Promise<void> {
    // Create a form data to append the file
    const formData = new FormData();
    formData.append("file", image);

    try {
      await $api(
        `/v1/application/hiluca/project/${project_id}/campaign/image`,
        {
          method: "POST",
          body: formData,
        },
      );

      return;
    } catch (error: any) {
      throw new Error("Failed to Upload Campaign Image");
    }
  },

  async getImage(
    projectId: number,
    allowUndefined?: boolean,
  ): Promise<Blob | undefined> {
    try {
      const response = await $api(
        `/v1/application/hiluca/project/${projectId}/campaign/image`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );

      return response as Blob;
    } catch (error: any) {
      if (allowUndefined) {
        return undefined;
      }

      throw new Error("Failed to get campaign image");
    }
  },
};
