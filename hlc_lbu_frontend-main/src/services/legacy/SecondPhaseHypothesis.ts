import { BaseApiResponseData } from "@/utils/type-declarations";
import { $api } from "../../utils/api";

export type HypothesisBuilderElementsResponse = BaseApiResponseData<{
  project_id: number;
  buyer_person: string;
  goals: Record<string, string[]>;
  hypothesis_elements: Record<string, string[]>;
}>;

export type FlattenedHypothesis = {
  project_id: number;
  buyer_person: string;
  goals: string[];
  hypothesis_elements: string[];
};

export type HypothesisBuilderOptionData = {
  Hypothesis_option: {
    id: number;
    Goal: string;
    Audience: string;
    preferred: number;
    Testing_Variable: string;
  };
};

export type HypothesisBuilderOptionListResponse = BaseApiResponseData<{
  project_id: number;
  hypothesis_builder_options: HypothesisBuilderOptionData[];
}>;

export type HypothesisBuilderPreferredOptionResponse = BaseApiResponseData<{
  project_id: number;
  option_id: number;
  hypothesis_builder_preferred_option: HypothesisBuilderOptionData;
}>;

export function processHypothesis(
  hypothesis: HypothesisBuilderElementsResponse,
): FlattenedHypothesis {
  const goals = hypothesis.data
    ? Object.values(hypothesis.data.goals).reduce(
        (acc, goal) => acc.concat(goal),
        [],
      )
    : [];
  const hypothesisElements = hypothesis.data
    ? Object.values(hypothesis.data?.hypothesis_elements).reduce(
        (acc, element) => acc.concat(element),
        [],
      )
    : [];

  return {
    project_id: Number(hypothesis.data?.project_id),
    buyer_person: hypothesis.data ? hypothesis.data.buyer_person : "",
    goals: goals,
    hypothesis_elements: hypothesisElements,
  };
}

export default {
  // servicio 7/18 de la fase 2 :  Select the Hypothesis That Best Aligns with your Goal 7
  async getOptionList(
    project_id: number,
  ): Promise<HypothesisBuilderOptionListResponse> {
    try {
      const response = await $api<HypothesisBuilderOptionListResponse>(
        `/v1/application/hiluca/project/${project_id}/hypothesis_builder/options`,
        {
          method: "GET",
          body: {
            project_id,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to get Hypothesis Builder Options");
    }
  },

  // servicio 8/18 de la fase 2 :  Select the Hypothesis That Best Aligns with your Goal 8
  async getBuilderElements(
    project_id: number,
  ): Promise<HypothesisBuilderElementsResponse> {
    try {
      const response = await $api<HypothesisBuilderElementsResponse>(
        `/v1/application/hiluca/project/${project_id}/hypothesis_builder/elements`,
        {
          method: "GET",
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to get Hypothesis Builder elements");
    }
  },

  //Save Hypothesis Builder Options

  // servicio 10/18 de la fase 2 :  Select the Hypothesis That Best Aligns with your Goal 10
  async saveOptionList(
    project_id: number,
    hypothesis_builder_options: HypothesisBuilderOptionData[],
  ): Promise<HypothesisBuilderOptionListResponse> {
    try {
      const res = await $api<HypothesisBuilderOptionListResponse>(
        `/v1/application/hiluca/project/hypothesis_builder/options`,
        {
          method: "POST",
          body: {
            project_id: project_id,
            hypothesis_builder_options: hypothesis_builder_options,
          },
        },
      );

      return res;
    } catch (error) {
      throw new Error("Failed to Save Hypothesis Builder Options");
    }
  },

  //Setting Preferred Option in Hypothesis Builder
  // servicio 11/18 de la fase 2 :  Select the Hypothesis That Best Aligns with your Goal 10
  async setPreferred(
    project_id: number,
    option_id: number,
  ): Promise<HypothesisBuilderPreferredOptionResponse> {
    try {
      const res = await $api<HypothesisBuilderPreferredOptionResponse>(
        `/v1/application/hiluca/project/hypothesis_builder/options/set_preferred`,
        {
          method: "POST",
          body: {
            project_id: project_id,
            option_id: option_id,
          },
        },
      );

      return res;
    } catch (error) {
      throw new Error(
        "Failed to Setting Preferred Option in Hypothesis Builder",
      );
    }
  },
};
