import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleProjectError, UnidentifiedError } from "../common-errors";

export class LandingPageHeroElementsNotFoundError extends Error {
  constructor() {
    super("LANDING_PAGE_HERO_ELEMENTS_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

export type LandingPageHeroElements = {
  Header: string[];
  Paragraph: string[];
  SubHeader: string[];
  CTA_Button_Text: string[];
};

export type LandingPageHeroElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_hero_section_generated: LandingPageHeroElements;
}>;

export type LandingPageHeroConfiguredElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_hero_section_configured: LandingPageHeroElements;
}>;

export type LandingPageHeroGenerateElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_hero_section_generated: LandingPageHeroElements;
}>;

export default {
  async getElements(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageHeroElementsResponse> {
    try {
      const response = await $api<LandingPageHeroElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/hero/elements`,
        {
          method: "GET",
        },
      );

      if (response.ok === 0) {
        throw response;
      }

      return response;
    } catch (error: any) {
      console.log("este es el error en getelements hero");
      console.log(error);
      handleProjectError(error);
      //return error
      throw new UnidentifiedError();
    }
  },

  async generate(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageHeroGenerateElementsResponse> {
    try {
      const response = await $api<LandingPageHeroGenerateElementsResponse>(
        `/v1/application/hiluca/project/landing_page/hero/generate`,
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
  ): Promise<LandingPageHeroConfiguredElementsResponse> {
    try {
      const response = await $api<LandingPageHeroConfiguredElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/hero`,
        {
          method: "GET",
        },
      );

      if (
        response.ok === 1 &&
        Object.keys(response.data.landing_page_hero_section_configured)
          .length === 0
      ) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new LandingPageHeroElementsNotFoundError();
    }
  },

  async getConfiguredOrGenerate(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageHeroElements> {
    // Fetch the hero. There could be three cases:
    // 1. The elements have never been generated.
    // 2. The elements have been generated but the hero has not been configured (saved).
    // 3. The elements have been generated and the hero has been configured (saved).

    let heroData: LandingPageHeroElements;

    try {
      // Try to get the configured hero.
      const response = await this.getConfigured(projectId, type);
      heroData = response.data.landing_page_hero_section_configured;
    } catch (error) {
      if (error instanceof LandingPageHeroElementsNotFoundError) {
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
          "CTA_Button_Text",
        ];
        const hasAllKeys = requiredKeys.every((key) =>
          Object.prototype.hasOwnProperty.call(
            response.data.landing_page_hero_section_generated,
            key,
          ),
        );
        // Let's see if the elements are generated.
        if (!hasAllKeys) {
          // The elements have not been generated, so let's generate them.
          heroData = (await this.generate(projectId, type)).data
            .landing_page_hero_section_generated;
        } else {
          heroData = response.data.landing_page_hero_section_generated;
          //  alert('perfecto este es el valor de heroData : ' + JSON.stringify(heroData))
        }
      } else {
        throw error;
      }
    }

    return heroData;
  },

  async configure(
    projectId: number | string,
    elements: LandingPageHeroElements,
    type: string,
  ): Promise<LandingPageHeroConfiguredElementsResponse> {
    try {
      const response = await $api<LandingPageHeroConfiguredElementsResponse>(
        `/v1/application/hiluca/project/landing_page/hero`,
        {
          method: "POST",
          body: {
            project_id: projectId,
            landing_page_hero_section_configured: elements,
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
