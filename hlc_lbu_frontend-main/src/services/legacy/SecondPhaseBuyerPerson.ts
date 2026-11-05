import { BaseApiResponseData, ImagePrompt } from "@/utils/type-declarations";
import { $api } from "../../utils/api";
import {
  handleProjectError,
  ImageNotFoundError,
  UnidentifiedError,
} from "../common-errors";
import { TargetBuyer } from "@/components/legacy/ad-generation/second-phase/cards/BuyerCard.vue";

export type InitProjectRefinationResponse = BaseApiResponseData<{
  project_id: number;
  assistand_id: string;
}>;

export interface BuyerPersonData {
  Buyer_Persona: {
    id: number;
    Age: number;
    Name: string;
    Title: string;
    Details: {
      Goals: string[];
      Lives: string;
      Needs: string[];
      Values: string;
      Pain_Points: string[];
    };
    preferred: number;
    Description: string;
  };
}

export type BuyerPersonListResponse = BaseApiResponseData<{
  project_id: number;
  buyer_persons: BuyerPersonData[];
}>;

export type BuyerPersonPromptListResponse = BaseApiResponseData<{
  project_id: number;
  buyer_person_image_prompts: ImagePrompt[];
}>;

export type BuyerPersonSelectedPromptResponse = BaseApiResponseData<{
  project_id: number;
  buyer_person_image_prompt_id: number;
  selected_buyer_person_image_prompt: ImagePrompt;
}>;

export type PreferredBuyerPersonResponse = BaseApiResponseData<{
  project_id: number;
  preferred_buyer_person: BuyerPersonData;
}>;

export default {
  mapSchemaToData(buyer: TargetBuyer): BuyerPersonData {
    return {
      Buyer_Persona: {
        id: buyer.id,
        preferred: buyer.selected ? 1 : 0,
        Title: buyer.title,
        Name: buyer.name,
        Age: buyer.age,
        Description: buyer.description,
        Details: {
          Lives: buyer.lives,
          Values: buyer.values,
          Goals: buyer.goals,
          Needs: buyer.needs,
          Pain_Points: buyer.painPoints,
        },
      },
    };
  },

  // servicio 1/18 de la fase 2 : Refine Your Growth Strategy 1
  async initializeProjectRefination(
    project_id: number,
  ): Promise<InitProjectRefinationResponse> {
    try {
      const response = await $api<InitProjectRefinationResponse>(
        "/v1/application/hiluca/project/refination",
        {
          method: "POST",
          body: {
            project_id,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  // servicio 2/18 de la fase 2 : Refine Your Growth Strategy 2
  async generate(project_id: number): Promise<BuyerPersonListResponse> {
    try {
      const response = await $api<BuyerPersonListResponse>(
        "/v1/application/hiluca/project/buyer_person/generate",
        {
          method: "POST",
          body: {
            project_id,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  // servicio 3/18 de la fase 2 :  Choose one buyer that fits your hypothesis   3
  async setPreferred(
    project_id: number,
    buyer_person_id: number,
  ): Promise<PreferredBuyerPersonResponse> {
    try {
      const response = await $api<PreferredBuyerPersonResponse>(
        "/v1/application/hiluca/project/buyer_person/set_preferred",
        {
          method: "POST",
          body: {
            project_id,
            buyer_person_id,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  async getPreferred(
    project_id: number,
  ): Promise<PreferredBuyerPersonResponse> {
    try {
      const response = await $api<PreferredBuyerPersonResponse>(
        `/v1/application/hiluca/project/${project_id}/preferred_buyer_person`,
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

  async savePreferred(
    project_id: number,
    preferred_buyer_person: BuyerPersonData,
  ): Promise<BuyerPersonListResponse> {
    try {
      const response = await $api<BuyerPersonListResponse>(
        "/v1/application/hiluca/project/preferred_buyer_person",
        {
          method: "POST",
          body: {
            project_id,
            preferred_buyer_person,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  // servicio 12/18 de la fase 2 :  Choose one buyer that fits your hypothesis (Generate image prompts) 12
  async generatePrompts(
    project_id: number,
  ): Promise<BuyerPersonPromptListResponse> {
    try {
      const response = await $api<BuyerPersonPromptListResponse>(
        "/v1/application/hiluca/project/preferred_buyer_person/image/prompts/generate",
        {
          method: "POST",
          body: {
            project_id,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  //Setting Preferred Image Prompt from Buyer Persona

  // servicio 13/18 de la fase 2 :  Choose one buyer that fits your hypothesis  13
  async setPreferredPrompt(
    project_id: number,
    buyer_person_image_prompt_id: number,
  ): Promise<BuyerPersonSelectedPromptResponse> {
    try {
      const response = await $api<BuyerPersonSelectedPromptResponse>(
        "/v1/application/hiluca/project/preferred_buyer_person/image/prompts/set_preferred",
        {
          method: "POST",
          body: {
            project_id,
            buyer_person_image_prompt_id,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  //Upload Buyer Person Image

  // servicio 15/18 de la fase 2 :  Choose one buyer that fits your hypothesis (Upload Buyer Person Image) 15
  async uploadImage(projectId: number, image: Blob): Promise<void> {
    // Create a form data to append the file
    const formData = new FormData();
    formData.append("file", image);

    try {
      await $api(
        `/v1/application/hiluca/project/${projectId}/buyer_person/image`,
        {
          method: "POST",
          body: formData,
        },
      );
      return;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  async getImage(
    projectId: number,
    allowUndefined?: boolean,
  ): Promise<Blob | undefined> {
    try {
      const response = await $api(
        `/v1/application/hiluca/project/${projectId}/buyer_person/image`,
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

      handleProjectError(error);
      throw new ImageNotFoundError();
    }
  },
};
