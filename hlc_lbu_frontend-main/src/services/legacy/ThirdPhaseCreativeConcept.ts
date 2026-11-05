import {
  BaseApiResponseData,
  RefinerAttributes,
} from "@/utils/type-declarations";
import { $api } from "../../utils/api";
import { CreativeConcept } from "@/components/legacy/ad-generation/third-phase/cards/LegacyCreativeConceptCard.vue";

export type CreativeConceptDescriptionData = {
  big_idea: string;
  time_frame: string;
  target_regions: string;
  consumer_insight: string;
  value_proposition: string;
  communication_objetive: string;
  tone_brand_personality: string;
};

export type DefineCreativeConceptResponse = BaseApiResponseData<{
  project_id: number;
  creative_concept_description: CreativeConceptDescriptionData;
  creative_concept_attributes_generated: RefinerAttributes;
}>;

export type CreativeConceptSetAttributesResponse = BaseApiResponseData<{
  project_id: number;
  creative_concept_attributes_generated: RefinerAttributes;
  creative_concept_attributes_saved: RefinerAttributes;
}>;

export type CreativeConceptData = {
  id: number;
  creative_concept: {
    title: string;
  };
  sections: {
    slogan: {
      text: string;
      title: string;
    };
    concept: {
      title: string;
      description: string;
    };
    message: {
      title: string;
      description: string;
    };
  };
  preferred: number;
};

export type CreativeConceptListResponse = BaseApiResponseData<{
  project_id: number;
  creative_concepts: CreativeConceptData[];
}>;

export type PreferredCreativeConceptResponse = BaseApiResponseData<{
  project_id: number;
  preferred_creative_concept: CreativeConceptData;
}>;

export default {
  //Define Creative Concept Description
  // servicio 4/17 de la fase 3 :  Add more details to define Creative Concept
  async saveDescription(
    project_id: number,
    creative_concept_description: CreativeConceptDescriptionData,
  ): Promise<DefineCreativeConceptResponse> {
    try {
      const response = await $api<DefineCreativeConceptResponse>(
        "/v1/application/hiluca/project/creative_concept/description",
        {
          method: "POST",
          body: {
            project_id,
            creative_concept_description,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to Define Creative Concept Description");
    }
  },

  //Define Creative Concepts Attibutes
  // servicio 5/17 de la fase 3 :  Creative Director refinement 5
  async saveAttributes(
    project_id: number,
    creative_concept_attributes_generated: RefinerAttributes,
    creative_concept_attributes_saved: RefinerAttributes,
  ): Promise<CreativeConceptSetAttributesResponse> {
    try {
      const response = await $api<CreativeConceptSetAttributesResponse>(
        "/v1/application/hiluca/project/creative_concept/attributes",
        {
          method: "POST",
          body: {
            project_id,
            creative_concept_attributes_generated,
            creative_concept_attributes_saved,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to Define Creative Concepts Attibutes");
    }
  },

  mapDataToSchema(campaignData: CreativeConceptData): CreativeConcept {
    return {
      id: campaignData.id,
      selected: campaignData.preferred === 1,
      title: campaignData.creative_concept.title,
      description: campaignData.creative_concept.title,
      concept: campaignData.sections.concept.description,
      message: campaignData.sections.message.description,
      slogan: campaignData.sections.slogan.text,
    };
  },

  mapSchemaToData(creativeConcept: CreativeConcept): CreativeConceptData {
    return {
      id: creativeConcept.id,
      creative_concept: {
        title: creativeConcept.title,
      },
      sections: {
        slogan: {
          text: creativeConcept.slogan,
          title: "Slogan",
        },
        concept: {
          title: "Concept",
          description: creativeConcept.concept,
        },
        message: {
          title: "Message",
          description: creativeConcept.message,
        },
      },
      preferred: creativeConcept.selected ? 1 : 0,
    };
  },

  async generate(project_id: number): Promise<CreativeConceptListResponse> {
    try {
      return await $api<CreativeConceptListResponse>(
        "/v1/application/hiluca/project/creative_concept/generate",
        {
          method: "POST",
          body: {
            project_id,
          },
        },
      );
    } catch (error) {
      throw new Error("Failed to generate creative concept");
    }
  },

  async setPreferred(
    project_id: number,
    c_concept_id: number,
  ): Promise<PreferredCreativeConceptResponse> {
    try {
      const response = await $api<PreferredCreativeConceptResponse>(
        "/v1/application/hiluca/project/creative_concept/set_preferred",
        {
          method: "POST",
          body: {
            project_id,
            c_concept_id,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to set the preferred creative concept");
    }
  },

  async savePreferred(
    project_id: number,
    preferred_creative_concept: CreativeConceptData,
  ): Promise<PreferredCreativeConceptResponse> {
    try {
      const response = await $api<PreferredCreativeConceptResponse>(
        "/v1/application/hiluca/project/creative_concept/preferred",
        {
          method: "POST",
          body: {
            project_id,
            preferred_creative_concept,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Failed to set save the preferred creative concept");
    }
  },
};
