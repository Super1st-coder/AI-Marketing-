import {
  BaseApiResponseData,
  ImagePrompt,
  RefinerAttributes,
} from "@/utils/type-declarations";
import { MetaAdData } from "./MetaAdsAPI";
import {
  handleProjectError,
  ProjectNotFoundError,
  UnidentifiedError,
} from "../common-errors";
import { GenericEmail, GenericEmailWithPreheader } from "./EmailsAPI";
import { BuyerPersonData } from "./SecondPhaseBuyerPerson";
import { ProductData } from "./SecondPhaseProduct";
import { HypothesisBuilderOptionData } from "./SecondPhaseHypothesis";
import { AudienceData } from "./ThirdPhaseAudience";
import {
  CreativeConceptData,
  CreativeConceptDescriptionData,
} from "./ThirdPhaseCreativeConcept";
import { CampaignData } from "./ThirdPhaseCampaigns";
import { WhatsappBotFunnelElements } from "./WhatsappBotFunnelAPI";

export type ProjectData = {
  id: number;
  name: string;
  createdAt: string;
  updatedAt: string;
  publishedAt: string;

  status?: string;

  // Hypothesis
  marketing_hypothesis?: string;

  // Product
  brand_name?: string;
  product_name?: string;
  product_url?: string;
  faq_product_url?: string;

  // Product refinement
  product_attributes_generated?: RefinerAttributes;
  product_attributes_saved?: RefinerAttributes;

  // Your target
  target_customer_description?: string;

  // Your target refinement
  target_customer_attributes_generated?: RefinerAttributes;
  target_customer_attributes_saved?: RefinerAttributes;

  // Element
  hypothesis_element_description?: string;

  // Element refinement
  hypothesis_element_attributes_generated?: RefinerAttributes;
  hypothesis_element_attributes_saved?: RefinerAttributes;

  // Goal
  goal_description?: string;

  // Goal refinement
  goal_attributes_generated?: RefinerAttributes;
  goal_attributes_saved?: RefinerAttributes;

  // Buyer challenge
  advantages_description?: string;

  // Buyer challenge refinement
  advantages_attributes_generated?: RefinerAttributes;
  advantages_attributes_saved?: RefinerAttributes;

  // Buyer persons
  buyer_persons?: BuyerPersonData[];
  preferred_buyer_person?: BuyerPersonData;
  buyer_person_image_prompts?: ImagePrompt[];
  selected_buyer_person_image_prompt?: ImagePrompt;

  // Products
  products?: ProductData[];
  preferred_product?: ProductData;

  // Hypothesis builder
  hypothesis_builder_options?: HypothesisBuilderOptionData[];
  hypothesis_builder_preferred_option?: HypothesisBuilderOptionData;

  // Audience
  audience?: AudienceData[];
  preferred_audience?: AudienceData;

  // Creative concept description
  creative_concept_description?: CreativeConceptDescriptionData;
  creative_concept_attributes_generated?: RefinerAttributes;
  creative_concept_attributes_saved?: RefinerAttributes;

  // Creative concepts
  creative_concepts?: CreativeConceptData[];
  preferred_creative_concept?: CreativeConceptData;

  // Campaigns
  campaigns?: CampaignData[];
  preferred_campaign?: CampaignData;
  campaign_image_prompts?: ImagePrompt[];
  selected_campaign_image_prompt?: ImagePrompt;

  // Meta ads
  meta_ads?: MetaAdData[];

  // Meta ads remarketing
  meta_ads_remarketing?: MetaAdData[];

  // Emails
  email_reminder_generated?: GenericEmail;
  email_painpoints_generated?: GenericEmailWithPreheader;
  email_usecase_generated?: GenericEmailWithPreheader;
  email_urgency_generated?: GenericEmailWithPreheader;
  email_offer_generated?: GenericEmailWithPreheader;

  // Whatsapp bot funnel
  whatsapp_bot_scheduling_generated?: WhatsappBotFunnelElements;
  whatsapp_bot_scheduling_configured?: WhatsappBotFunnelElements;
};

export type SimpleProjectData = {
  id: number;
  name: string;
  brand_name?: string;
  product_name?: string;
};

export type CreateProjectResponse = BaseApiResponseData<{
  id: number;
}>;

export type ProjectResponse = BaseApiResponseData<ProjectData>;

export type ProjectListResponse = BaseApiResponseData<SimpleProjectData[]>;

export default {
  // Primer servicio de la fase 1 : Create Project
  async create(name: string): Promise<CreateProjectResponse> {
    try {
      const response = await $api<CreateProjectResponse>(
        "/v1/application/hiluca/project",
        {
          method: "POST",
          body: {
            name,
          },
        },
      );

      return response;
    } catch (error) {
      throw new Error("Error adding project");
    }
  },

  async getOne(projectId: number | string): Promise<ProjectResponse> {
    try {
      const response = await $api<ProjectResponse>(
        `/v1/application/hiluca/project/${projectId}`,
        {
          method: "GET",
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);

      // For some reason, in this endpoint, if the project does not exist,
      // the error is not "ERROR - Project NOT Found" but "ERROR - Saving Project"
      if (error.message?.text === "ERROR - Saving Project")
        throw new ProjectNotFoundError();

      throw new UnidentifiedError();
    }
  },

  async getList() {
    try {
      const response = await $api<ProjectListResponse>(
        "/v1/application/hiluca/project",
        {
          method: "GET",
        },
      );

      return response;
    } catch (error: any) {
      throw new UnidentifiedError();
    }
  },

  async setStatus(projectId: number | string, status: string) {
    try {
      const response = await $api<ProjectListResponse>(
        "/v1/application/hiluca/project/status",
        {
          method: "PUT",
          body: {
            project_id: projectId,
            status: status,
          },
        },
      );

      return response;
    } catch (error: any) {
      throw new UnidentifiedError();
    }
  },
};
