import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleProjectError, UnidentifiedError } from "../common-errors";

export class LandingPageTestimonialElementsNotFoundError extends Error {
  constructor() {
    super("LANDING_PAGE_TESTIMONIAL_ELEMENTS_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

export type TestimonialContent = {
  Review: string[];
  User_Name: string[];
};
export type LandingPageTestimonialElements = {
  Header: string[];
  Testimonial_1: TestimonialContent;
  Testimonial_2: TestimonialContent;
  Testimonial_3: TestimonialContent;
};
export type LandingPageTestimonialElementsResponse = BaseApiResponseData<{
  project_id: number;
  landing_page_testimonial_section_generated: LandingPageTestimonialElements;
}>;

export type LandingPageTestimonialConfiguredElementsResponse =
  BaseApiResponseData<{
    project_id: number;
    landing_page_testimonial_section_configured: LandingPageTestimonialElements;
  }>;

export type LandingPageTestimonialGenerateElementsResponse =
  BaseApiResponseData<{
    project_id: number;
    landing_page_testimonial_section_generated: LandingPageTestimonialElements;
  }>;

export function getTestimonialReviewWithUser(
  testimonial: TestimonialContent,
): string[] {
  try {
    // Check if Review and User_Name arrays exist and have the same length
    if (
      !testimonial.Review ||
      !testimonial.User_Name ||
      testimonial.Review.length !== testimonial.User_Name.length
    ) {
      console.warn("Invalid testimonial data:", testimonial);
      return testimonial.Review || []; // Return original reviews or empty array if invalid
    }

    // Combine reviews and usernames
    return testimonial.Review.map((review, index) => {
      return `${review}\n\n${testimonial.User_Name[index]}`;
    });
  } catch (error) {
    console.error("Error processing testimonials:", error);
    return []; // Return original reviews or empty array on error
  }
}

export default {
  async getElements(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageTestimonialElementsResponse> {
    try {
      const response = await $api<LandingPageTestimonialElementsResponse>(
        `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/testimonial/elements`,
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
  ): Promise<LandingPageTestimonialGenerateElementsResponse> {
    try {
      const response =
        await $api<LandingPageTestimonialGenerateElementsResponse>(
          `/v1/application/hiluca/project/landing_page/testimonial/generate`,
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
  ): Promise<LandingPageTestimonialConfiguredElementsResponse> {
    try {
      const response =
        await $api<LandingPageTestimonialConfiguredElementsResponse>(
          `/v1/application/hiluca/project/${projectId}/landing_page/type/${type}/testimonial`,
          {
            method: "GET",
          },
        );

      if (
        response.ok === 1 &&
        Object.keys(response.data.landing_page_testimonial_section_configured)
          .length === 0
      ) {
        throw response;
      }

      return response;
    } catch (error: any) {
      handleProjectError(error);

      throw new LandingPageTestimonialElementsNotFoundError();
    }
  },

  async getConfiguredOrGenerate(
    projectId: number | string,
    type: string,
  ): Promise<LandingPageTestimonialElements> {
    // Fetch the hero. There could be three cases:
    // 1. The elements have never been generated.
    // 2. The elements have been generated but the hero has not been configured (saved).
    // 3. The elements have been generated and the hero has been configured (saved).

    let testimonialData: LandingPageTestimonialElements;

    try {
      // Try to get the configured hero.
      const response = await this.getConfigured(projectId, type);
      testimonialData =
        response.data.landing_page_testimonial_section_configured;
    } catch (error) {
      if (error instanceof LandingPageTestimonialElementsNotFoundError) {
        // The hero is not configured, that could leave us two cases:
        // 1. The elements have not been generated.
        // 2. The elements could have been generated but the hero has not been configured (saved).

        // Let's try to fetch the elements
        const response = await this.getElements(projectId, type);
        // Let's see if the elements are generated.
        const requiredKeys = [
          "Header",
          "Testimonial_1",
          "Testimonial_2",
          "Testimonial_3",
        ];

        const hasAllKeys = requiredKeys.every((key) =>
          Object.prototype.hasOwnProperty.call(
            response.data.landing_page_testimonial_section_generated,
            key,
          ),
        );
        // Let's see if the elements are generated.
        if (!hasAllKeys) {
          // The elements have not been generated, so let's generate them.
          testimonialData = (await this.generate(projectId, type)).data
            .landing_page_testimonial_section_generated;
        } else {
          testimonialData =
            response.data.landing_page_testimonial_section_generated;
        }
      } else {
        throw error;
      }
    }

    return testimonialData;
  },

  async configure(
    projectId: number | string,
    elements: LandingPageTestimonialElements,
    type: string,
  ): Promise<LandingPageTestimonialConfiguredElementsResponse> {
    try {
      const response =
        await $api<LandingPageTestimonialConfiguredElementsResponse>(
          `/v1/application/hiluca/project/landing_page/testimonial`,
          {
            method: "POST",
            body: {
              project_id: projectId,
              landing_page_testimonial_section_configured: elements,
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
