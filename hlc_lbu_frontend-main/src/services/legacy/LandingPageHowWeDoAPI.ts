import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleProjectError, UnidentifiedError } from "../common-errors";

export class LandingPageHowWeDoElementsNotFoundError extends Error {
  constructor() {
    super("LANDING_PAGE_HOW_WE_DO_ELEMENTS_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

//ok
export type StepProcessElement = {
  Paragraph: string[];
  Subheader: string[];
};
//ok
export type LandingPageHowWeDoElements = {
  Header: string[];
  Step_Process_1: StepProcessElement;
  Step_Process_2: StepProcessElement;
  Step_Process_3: StepProcessElement;
  CTA_Button_Text: string[];
  Action_Paragraph: string[];
};
//ok
export type LandingPageHowWeDoElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_howwedo_section_generated: LandingPageHowWeDoElements;
}>;
//ok
export type LandingPageHowWeDoConfiguredElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_howwedo_section_configured: LandingPageHowWeDoElements;
}>;
//OK
export type LandingPageHowWeDoGenerateElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_howwedo_section_generated: LandingPageHowWeDoElements;
}>;

export default {
  async getElements(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageHowWeDoElementsResponse> {
    try {
      const response = await $api<LandingPageHowWeDoElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/howwedo/elements`,
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

      throw new UnidentifiedError();
    }
  },

  async generate(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageHowWeDoGenerateElementsResponse> {
    try {
      const response = await $api<LandingPageHowWeDoGenerateElementsResponse>(
        `/v1/application/hiluca/project/landing_page/howwedo/generate`,
        {
          method: "POST",
          body: {
            project_id: projectId,
            type: type,
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

  async getConfigured(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageHowWeDoConfiguredElementsResponse> {
    try {
      const response = await $api<LandingPageHowWeDoConfiguredElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/howwedo`,
        {
          method: "GET",
        },
      );

      if (
        response.ok === 1 &&
        Object.keys(response.data.landing_page_howwedo_section_configured)
          .length === 0
      ) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new LandingPageHowWeDoElementsNotFoundError();
    }
  },
  //ok
  async getConfiguredOrGenerate(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageHowWeDoElements> {
    // Fetch the hero. There could be three cases:
    // 1. The elements have never been generated.
    // 2. The elements have been generated but the hero has not been configured (saved).
    // 3. The elements have been generated and the hero has been configured (saved).

    let howwedoData: LandingPageHowWeDoElements;

    try {
      // Try to get the configured hero.
      const response = await this.getConfigured(projectId, type);
      howwedoData = response.data.landing_page_howwedo_section_configured;
    } catch (error) {
      if (error instanceof LandingPageHowWeDoElementsNotFoundError) {
        // The hero is not configured, that could leave us two cases:
        // 1. The elements have not been generated.
        // 2. The elements could have been generated but the hero has not been configured (saved).

        // Let's try to fetch the elements
        const response = await this.getElements(projectId, type);

        // Let's see if the elements are generated.
        const requiredKeys = [
          "Header",
          "Step_Process_1",
          "Step_Process_2",
          "Step_Process_3",
          "CTA_Button_Text",
          "Action_Paragraph",
        ];
        const hasAllKeys = requiredKeys.every((key) =>
          Object.prototype.hasOwnProperty.call(
            response.data.landing_page_howwedo_section_generated,
            key,
          ),
        );

        // Let's see if the elements are generated.
        if (!hasAllKeys) {
          // The elements have not been generated, so let's generate them.
          howwedoData = (await this.generate(projectId, type)).data
            .landing_page_howwedo_section_generated;
        } else {
          howwedoData = response.data.landing_page_howwedo_section_generated;
        }
      } else {
        throw error;
      }
    }

    return howwedoData;
  },

  async configure(
    projectId: number | string,
    elements: LandingPageHowWeDoElements,
    type: string,
  ): Promise<LandingPageHowWeDoConfiguredElementsResponse> {
    try {
      const response = await $api<LandingPageHowWeDoConfiguredElementsResponse>(
        `/v1/application/hiluca/project/landing_page/howwedo`,
        {
          method: "POST",
          body: {
            project_id: projectId,
            landing_page_howwedo_section_configured: elements,
            type: type,
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
};
