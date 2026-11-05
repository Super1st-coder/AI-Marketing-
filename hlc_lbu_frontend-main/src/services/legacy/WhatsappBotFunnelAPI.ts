import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleProjectError, UnidentifiedError } from "../common-errors";

export const whatsappBotFunnelTypes = [
  "information_and_support_bot",
  "appointment_scheduling_bot",
  "contact_directory_bot",
] as const;
export type WhatsappBotFunnelType = (typeof whatsappBotFunnelTypes)[number];

export type WhatsappBotFunnelElements = {
  WhatsApp_Conversational_Flow?: {
    Section_5_Flow_A_Goodbye_Options: string[];
    Section_1_Initial_Greeting_Message: string[];
    Section_4_Flow_A_Choose_Hours_Options: string[];
    Section_6_Flow_B_Connect_With_An_Agent: string[];
    Section_2_Follow_Up_Greeting_With_Options: string[];
    Section_3_Flow_A_Days_Of_The_Week_Options: string[];
    Section_7_Flow_B_Agent_Handoff_Confirmation: string[];
    "follow-up-greeting_options"?: string[];
    day_options?: string[];
    time_slot_options?: string[];
    details_options?: string[];
  };
  selected_type?: WhatsappBotFunnelType;
};

export type WhatsappBotFunnelElementsResponse = BaseApiResponseData<{
  project_id: number;
  whatsapp_bot_scheduling_generated: WhatsappBotFunnelElements;
  whatsapp_bot_scheduling_custom_tone_message: string;
}>;

export type LandingPageHeroConfiguredElementsResponse = BaseApiResponseData<{
  project_id: number;
  whatsapp_bot_scheduling_configured: WhatsappBotFunnelElements;
}>;

export default {
  async getElements(
    projectId: number | string,
  ): Promise<WhatsappBotFunnelElementsResponse> {
    try {
      const response = await $api<WhatsappBotFunnelElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/whatsapp_bot/scheduling/elements`,
        {
          method: "GET",
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  async generateElements(
    project_id: number | string,
    custom_tone_message: string,
  ): Promise<WhatsappBotFunnelElementsResponse> {
    try {
      const response = await $api<WhatsappBotFunnelElementsResponse>(
        `/v1/application/hiluca/project/whatsapp_bot/scheduling/generate`,
        {
          method: "POST",
          body: {
            project_id,
            custom_tone_message,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  async getConfigured(
    projectId: number | string,
  ): Promise<LandingPageHeroConfiguredElementsResponse> {
    try {
      const response = await $api<LandingPageHeroConfiguredElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/whatsapp_bot/scheduling`,
        {
          method: "GET",
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  async configure(
    projectId: number | string,
    elements: WhatsappBotFunnelElements,
  ): Promise<LandingPageHeroConfiguredElementsResponse> {
    try {
      const response = await $api<LandingPageHeroConfiguredElementsResponse>(
        `/v1/application/hiluca/project/whatsapp_bot/scheduling`,
        {
          method: "POST",
          body: {
            project_id: projectId,
            whatsapp_bot_scheduling_configured: elements,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  async getConfiguredOrGenerated(
    projectId: number | string,
  ): Promise<WhatsappBotFunnelElements> {
    try {
      const response = await this.getConfigured(projectId);
      let data: WhatsappBotFunnelElements | undefined =
        response.data.whatsapp_bot_scheduling_configured;

      if (!data) {
        // Let's try to fetch the elements
        const response = await this.getElements(projectId);
        data = response.data.whatsapp_bot_scheduling_generated;
      }

      if (!data) {
        throw new Error("WHATSAPP_BOT_FUNNEL_NOT_GENERATED");
      }

      return data;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },
};
