import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleProjectError, UnidentifiedError } from "../common-errors";

export class LandingPageCompetiAdvantagesElementsNotFoundError extends Error {
  constructor() {
    super("LANDING_PAGE_COMPETITIVE_ADVANTAGES_ELEMENTS_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

export type LandingPageCompetiAdvantagesElements = {
  Header: string[];
  Paragraph: string[];
  SubHeader: string[];
  Action_Paragraph: string[];
  CTA_Button_Text_1: string[];
  CTA_Button_Text_2: string[];
};

export type LandingPageCompetiAdvantagesElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_competitive_advantages_section_generated: LandingPageCompetiAdvantagesElements;
}>;

export type LandingPageCompetiAdvantagesConfiguredElementsResponse =
  BaseApiResponseData<{
    project_id: number;
    landing_page_competitive_advantages_section_configured: LandingPageCompetiAdvantagesElements;
  }>;

export type LandingPageCompetiAdvantagesGenerateElementsResponse =
  BaseApiResponseData<{
    project_id: number;
    landing_page_competitive_advantages_section_generated: LandingPageCompetiAdvantagesElements;
  }>;

export default {
  async getElements(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageCompetiAdvantagesElementsResponse> {
    try {
      const response = await $api<LandingPageCompetiAdvantagesElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/competitive_advantages/elements`,
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
  ): Promise<LandingPageCompetiAdvantagesGenerateElementsResponse> {
    try {
      const response =
        await $api<LandingPageCompetiAdvantagesGenerateElementsResponse>(
          `/v1/application/hiluca/project/landing_page/competitive_advantages/generate`,
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
  ): Promise<LandingPageCompetiAdvantagesConfiguredElementsResponse> {
    try {
      const response =
        await $api<LandingPageCompetiAdvantagesConfiguredElementsResponse>(
          `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/competitive_advantages`,
          {
            method: "GET",
          },
        );

      if (
        response.ok === 1 &&
        Object.keys(
          response.data.landing_page_competitive_advantages_section_configured,
        ).length === 0
      ) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new LandingPageCompetiAdvantagesElementsNotFoundError();
    }
  },

  async getConfiguredOrGenerate(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageCompetiAdvantagesElements> {
    // Fetch the hero. There could be three cases:
    // 1. The elements have never been generated.
    // 2. The elements have been generated but the hero has not been configured (saved).
    // 3. The elements have been generated and the hero has been configured (saved).

    let competitiveAdvantagesData: LandingPageCompetiAdvantagesElements;
    try {
      // Try to get the configured hero.
      const response = await this.getConfigured(projectId, type);
      competitiveAdvantagesData =
        response.data.landing_page_competitive_advantages_section_configured;
    } catch (error) {
      if (error instanceof LandingPageCompetiAdvantagesElementsNotFoundError) {
        // The hero is not configured, that could leave us two cases:
        // 1. The elements have not been generated.
        // 2. The elements could have been generated but the hero has not been configured (saved).

        // Let's try to fetch the elements
        const response = await this.getElements(projectId, type);
        // Let's see if the elements are generated.
        const requiredKeys = [
          "Header",
          "Paragraph",
          "SubHeader",
          "Action_Paragraph",
          "CTA_Button_Text_1",
          "CTA_Button_Text_2",
        ];
        const hasAllKeys = requiredKeys.every((key) =>
          Object.prototype.hasOwnProperty.call(
            response.data.landing_page_competitive_advantages_section_generated,
            key,
          ),
        );
        // Let's see if the elements are generated.
        if (!hasAllKeys) {
          // The elements have not been generated, so let's generate them.
          competitiveAdvantagesData = (await this.generate(projectId, type))
            .data.landing_page_competitive_advantages_section_generated;
        } else {
          competitiveAdvantagesData =
            response.data.landing_page_competitive_advantages_section_generated;
        }
      } else {
        throw error;
      }
    }

    return competitiveAdvantagesData;
  },

  async configure(
    projectId: number | string,
    elements: LandingPageCompetiAdvantagesElements,
    type: string,
  ): Promise<LandingPageCompetiAdvantagesConfiguredElementsResponse> {
    try {
      const response =
        await $api<LandingPageCompetiAdvantagesConfiguredElementsResponse>(
          `/v1/application/hiluca/project/landing_page/competitive_advantages`,
          {
            method: "POST",
            body: {
              project_id: projectId,
              landing_page_competitive_advantages_section_configured: elements,
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
