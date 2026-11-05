import { $api } from "../../utils/api";
import { BaseApiResponseData } from "@/utils/type-declarations";

export type AudienceData = {
  id: number;
  Audience: string;
  Interests: string[];
  preferred: number;
  Demographics: {
    Age: string;
    Gender: string;
    Location: string[];
    IncomeLevel: string;
  };
  AudienceSegment: string;
};

export type GenerateAudiencesResponse = BaseApiResponseData<{
  project_id: number;
  audience: AudienceData[];
}>;

export default {
  //Generate Audiences
  // servicio 1/17 de la fase 3 :  Build Your Creative Campaign Strategy 1
  async generate(project_id: number): Promise<GenerateAudiencesResponse> {
    try {
      const res: GenerateAudiencesResponse = await $api(
        "/v1/application/hiluca/project/audience/generate",
        {
          method: "POST",
          body: {
            project_id: project_id,
          },
        },
      );

      return res;
    } catch (error) {
      throw new Error("Failed to Generate Audiences");
    }
  },

  //Setting Preferred Audience
  // servicio 2/17 de la fase 3 :  Select the audience you’d like to test the hipothesis for 2
  async setPreferred(project_id: number, audience_id: number): Promise<number> {
    try {
      const res: any = await $api(
        "/v1/application/hiluca/project/audience/set_preferred",
        {
          method: "POST",
          body: {
            project_id,
            audience_id,
          },
        },
      );

      return res.ok;
    } catch (error) {
      throw new Error("Failed to Setting Preferred Audience");
    }
  },

  //Save Preferred Audience
  // servicio 3/17 de la fase 3 :  Select the audience you’d like to test the hipothesis for 3
  async savePreferred(
    project_id: number,
    preferred_audience: {},
  ): Promise<number> {
    try {
      const res: any = await $api(
        "/v1/application/hiluca/project/preferred_audience",
        {
          method: "POST",
          body: {
            project_id,
            preferred_audience,
          },
        },
      );

      return res.ok;
    } catch (error) {
      throw new Error("Failed to Save Preferred Audience");
    }
  },
};
