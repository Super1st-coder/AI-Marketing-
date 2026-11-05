import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleProjectError, UnidentifiedError } from "../common-errors";

export class LandingPageBenefitsElementsNotFoundError extends Error {
  constructor() {
    super("LANDING_PAGE_BENEFITS_ELEMENTS_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

export type ImageElement = {
  Alt_text: string[];
  Description: string[];
};

export type LandingPageBenefitsElements = {
  Image: ImageElement;
  Header: string[];
  Paragraph: string[];
  CTA_Button_Text: string[];
  Action_Paragraph: string[];
};

export type LandingPageBenefitsElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_benefits_section_generated: LandingPageBenefitsElements;
}>;

export type LandingPageBenefitsConfiguredElementsResponse =
  BaseApiResponseData<{
    project_id: number;
    landing_page_benefits_section_configured: LandingPageBenefitsElements;
  }>;

export type LandingPageBenefitsGenerateElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_benefits_section_generated: LandingPageBenefitsElements;
}>;

export default {
  async getElements(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageBenefitsElementsResponse> {
    try {
      const response = await $api<LandingPageBenefitsElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/benefits/elements`,
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
  ): Promise<LandingPageBenefitsGenerateElementsResponse> {
    try {
      const response = await $api<LandingPageBenefitsGenerateElementsResponse>(
        `/v1/application/hiluca/project/landing_page/benefits/generate`,
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
  ): Promise<LandingPageBenefitsConfiguredElementsResponse> {
    try {
      const response =
        await $api<LandingPageBenefitsConfiguredElementsResponse>(
          `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/benefits`,
          {
            method: "GET",
          },
        );

      if (
        response.ok === 1 &&
        Object.keys(response.data.landing_page_benefits_section_configured)
          .length === 0
      ) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new LandingPageBenefitsElementsNotFoundError();
    }
  },
  async getConfiguredOrGenerate(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageBenefitsElements> {
    // Fetch the hero. There could be three cases:
    // 1. The elements have never been generated.
    // 2. The elements have been generated but the hero has not been configured (saved).
    // 3. The elements have been generated and the hero has been configured (saved).

    let benefitsData: LandingPageBenefitsElements;

    try {
      // Try to get the configured hero.
      const response = await this.getConfigured(projectId, type);
      benefitsData = response.data.landing_page_benefits_section_configured;
    } catch (error) {
      if (error instanceof LandingPageBenefitsElementsNotFoundError) {
        // The hero is not configured, that could leave us two cases:
        // 1. The elements have not been generated.
        // 2. The elements could have been generated but the hero has not been configured (saved).

        // Let's try to fetch the elements
        const response = await this.getElements(projectId, type);

        // Let's see if the elements are generated.
        const requiredKeys = [
          "Header",
          "Image",
          "Paragraph",
          "CTA_Button_Text",
          "Action_Paragraph",
        ];
        const hasAllKeys = requiredKeys.every((key) =>
          Object.prototype.hasOwnProperty.call(
            response.data.landing_page_benefits_section_generated,
            key,
          ),
        );

        // Let's see if the elements are generated.
        if (!hasAllKeys) {
          // The elements have not been generated, so let's generate them.
          benefitsData = (await this.generate(projectId, type)).data
            .landing_page_benefits_section_generated;
        } else {
          benefitsData = response.data.landing_page_benefits_section_generated;
        }
      } else {
        throw error;
      }
    }

    return benefitsData;
  },
  //ok
  async configure(
    projectId: number | string,
    elements: LandingPageBenefitsElements,
    type: string,
  ): Promise<LandingPageBenefitsConfiguredElementsResponse> {
    try {
      const response =
        await $api<LandingPageBenefitsConfiguredElementsResponse>(
          `/v1/application/hiluca/project/landing_page/benefits`,
          {
            method: "POST",
            body: {
              project_id: projectId,
              landing_page_benefits_section_configured: elements,
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
