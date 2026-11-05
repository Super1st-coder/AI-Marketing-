import { object, string, number, InferType } from "yup";

// Define el esquema para una sección
const sectionSchema = object({
  text: string().required().trim(),
  title: string().required(),
});

// Define el esquema para el objeto de secciones
export const sectionsSchema = object().shape({
  cta: sectionSchema,
  budget: sectionSchema,
  funnel_flow: sectionSchema,
  creative_types: sectionSchema,
  execution_steps: sectionSchema,
  campaign_details: sectionSchema,
  short_description: sectionSchema,
});

// Define el esquema para el concepto de campaña
export const campaignConceptSchema = object().shape({
  id: number().required(),
  campaign: object().shape({
    title: string().required().trim(),
  }),
  sections: sectionsSchema,
  preferred: number().required(),
});

export type CampaignConcept = InferType<typeof campaignConceptSchema>;
