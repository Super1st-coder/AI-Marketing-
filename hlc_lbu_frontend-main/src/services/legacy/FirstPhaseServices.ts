import {
  BaseApiResponseData,
  RefinerAttributes,
} from "@/utils/type-declarations";
import { $api } from "../../utils/api";

export type DefineMarketingHypothesisResponse = BaseApiResponseData<{
  project_id: number;
  marketing_hypothesis: string;
  marketing_hypothesis_analysis: {
    buyer_persona: string;
    element_to_test: string;
    prediction: string;
  };
}>;

export type DefineProductDescriptionResponse = BaseApiResponseData<{
  project_id: number;
  product_attributes_generated: RefinerAttributes;
}>;

export type DefineProductAttributesResponse = BaseApiResponseData<{
  project_id: number;
  product_attributes_generated: RefinerAttributes;
  product_attributes_saved: RefinerAttributes;
}>;

export type DefineTargetCustomerResponse = BaseApiResponseData<{
  project_id: number;
  target_customer_description: string;
  target_customer_attributes_generated: RefinerAttributes;
}>;

export type DefineTargetCustomerAttributesResponse = BaseApiResponseData<{
  project_id: number;
  target_customer_attributes_generated: RefinerAttributes;
  target_customer_attributes_saved: RefinerAttributes;
}>;

export type DefineHypothesisDescriptionResponse = BaseApiResponseData<{
  project_id: number;
  hypothesis_element_description: string;
  hypothesis_element_attributes_generated: RefinerAttributes;
}>;

export type DefineHypothesisAttributesResponse = BaseApiResponseData<{
  project_id: number;
  hypothesis_element_attributes_generated: RefinerAttributes;
  hypothesis_element_attributes_saved: RefinerAttributes;
}>;

export type DefineGoalDescriptionResponse = BaseApiResponseData<{
  project_id: number;
  goal_description: string;
  goal_attributes_generated: RefinerAttributes;
}>;

export type DefineGoalAttributesResponse = BaseApiResponseData<{
  project_id: number;
  goal_attributes_generated: RefinerAttributes;
  goal_attributes_saved: RefinerAttributes;
}>;

export type DefineAdvantagesDescriptionResponse = BaseApiResponseData<{
  project_id: number;
  advantages_description: string;
  advantages_attributes_generated: RefinerAttributes;
}>;

export type DefineAdvantagesAttributesResponse = BaseApiResponseData<{
  project_id: number;
  advantages_attributes_generated: RefinerAttributes;
  advantages_attributes_saved: RefinerAttributes;
}>;

export default {
  // segundo servicio de la fase 1 : What business hypothesis would you like to validate?
  async defineMarketingHypothesis(
    project_id: number,
    marketing_hypothesis: string,
  ): Promise<DefineMarketingHypothesisResponse> {
    try {
      const response = await $api<DefineMarketingHypothesisResponse>(
        "/v1/application/hiluca/project/marketing-hypothesis",
        {
          method: "POST",
          body: {
            project_id,
            marketing_hypothesis,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to add marketing hypothesis ");
    }
  },

  // tercer servicio de la fase 1: What’s Your Product Offering?
  async defineProductDescription(
    project_id: number,
    brand_name: string,
    product_name: string,
    product_url: string,
    faq_product_url: string,
  ): Promise<DefineProductDescriptionResponse> {
    try {
      const response = await $api<DefineProductDescriptionResponse>(
        "/v1/application/hiluca/project/product/description",
        {
          method: "POST",
          body: {
            project_id,
            brand_name,
            product_name,
            product_url,
            faq_product_url,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to add Product Description");
    }
  },

  // cuarto servicio de la fase 1: Refine Your Product Details
  async defineProductAttributes(
    project_id: number,
    product_attributes_generated: RefinerAttributes,
    product_attributes_saved: RefinerAttributes,
  ): Promise<DefineProductAttributesResponse> {
    try {
      const response = await $api<DefineProductAttributesResponse>(
        "/v1/application/hiluca/project/product/attributes",
        {
          method: "POST",
          body: {
            project_id,
            product_attributes_generated,
            product_attributes_saved,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to add Product Attributes");
    }
  },

  // quinto servicio de la fase 1: Who is Your Target Customer?
  async defineTargetConsumerDescription(
    project_id: number,
    target_customer_description: string,
  ): Promise<DefineTargetCustomerResponse> {
    try {
      const response = await $api<DefineTargetCustomerResponse>(
        "/v1/application/hiluca/project/target_customer/description",
        {
          method: "POST",
          body: {
            project_id,
            target_customer_description,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to add Product Attributes");
    }
  },

  // sexto servicio de la fase 1 : Refine Your Buyer Persona Details
  async defineTargetConsumerAttributes(
    project_id: number,
    target_customer_attributes_generated: RefinerAttributes,
    target_customer_attributes_saved: RefinerAttributes,
  ): Promise<DefineTargetCustomerAttributesResponse> {
    try {
      const response = await $api<DefineTargetCustomerAttributesResponse>(
        "/v1/application/hiluca/project/target_customer/attributes",
        {
          method: "POST",
          body: {
            project_id,
            target_customer_attributes_generated,
            target_customer_attributes_saved,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to add Target Consumer Attributes");
    }
  },

  // septimo servicio de la fase 1 : What is the Element you want to test for this Hypothesis?
  async defineHypothesisDescription(
    project_id: number,
    hypothesis_element_description: string,
  ): Promise<DefineHypothesisDescriptionResponse> {
    try {
      const response = await $api<DefineHypothesisDescriptionResponse>(
        "/v1/application/hiluca/project/hypothesis/description",
        {
          method: "POST",
          body: {
            project_id,
            hypothesis_element_description,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to define Hypothesis Description");
    }
  },

  // octavo servicio de la fase 1 : Refine and Add Elements to Test your Hypothesis
  async defineHypothesisAttributes(
    project_id: number,
    hypothesis_element_attributes_generated: RefinerAttributes,
    hypothesis_element_attributes_saved: RefinerAttributes,
  ): Promise<DefineHypothesisAttributesResponse> {
    try {
      const response = await $api<DefineHypothesisAttributesResponse>(
        "/v1/application/hiluca/project/hypothesis/attributes",
        {
          method: "POST",
          body: {
            project_id: project_id,
            hypothesis_element_attributes_generated,
            hypothesis_element_attributes_saved,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to define Hypothesis Attributes");
    }
  },

  // noveno servicio de la fase 1 : What is your Goal you want to achieve?
  async defineGoalDescription(
    project_id: number,
    goal_description: string,
  ): Promise<DefineGoalDescriptionResponse> {
    try {
      const response = await $api<DefineGoalDescriptionResponse>(
        "/v1/application/hiluca/project/goal/description",
        {
          method: "POST",
          body: {
            project_id: project_id,
            goal_description: goal_description,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to define Goal Description");
    }
  },

  // decimo servicio de la fase 1 : Refine Your Goal Variants
  async defineGoalAttributes(
    project_id: number,
    goal_attributes_generated: RefinerAttributes,
    goal_attributes_saved: RefinerAttributes,
  ): Promise<DefineGoalAttributesResponse> {
    try {
      const response = await $api<DefineGoalAttributesResponse>(
        "/v1/application/hiluca/project/goal/attributes",
        {
          method: "POST",
          body: {
            project_id: project_id,
            goal_attributes_generated: goal_attributes_generated,
            goal_attributes_saved: goal_attributes_saved,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to define Goal Attributes");
    }
  },

  // decimo primer servicio de la fase 1 : How does your product help solve the buyer’s challenge better than anyone else?
  async defineAdvantagesDescription(
    project_id: number,
    advantages_description: string,
  ): Promise<DefineAdvantagesDescriptionResponse> {
    try {
      const response = await $api<DefineAdvantagesDescriptionResponse>(
        "/v1/application/hiluca/project/advantages/description",
        {
          method: "POST",
          body: {
            project_id: project_id,
            advantages_description: advantages_description,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to define Advantages Description");
    }
  },

  // decimo segundo servicio de la fase 1 : Refine and Add Competitive Advantages to Test your Hypothesis
  async defineAdvantagesAttributes(
    project_id: number,
    advantages_attributes_generated: RefinerAttributes,
    advantages_attributes_saved: RefinerAttributes,
  ): Promise<DefineAdvantagesAttributesResponse> {
    try {
      const response = await $api<DefineAdvantagesAttributesResponse>(
        "/v1/application/hiluca/project/advantages/attributes",
        {
          method: "POST",
          body: {
            project_id: project_id,
            advantages_attributes_generated: advantages_attributes_generated,
            advantages_attributes_saved: advantages_attributes_saved,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to define Advantages Attributes");
    }
  },
};
