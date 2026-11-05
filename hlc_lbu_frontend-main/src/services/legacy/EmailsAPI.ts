import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleProjectError, UnidentifiedError } from "../common-errors";

export type GenericEmail = {
  Body?: string;
  "Video CTA"?: string;
  Introduction?: string;
  "Subject Line"?: string;
  "Closing and Final CTA"?: string;
  "Objections and Reassurance"?: string;
};

export type GenericEmailWithPreheader = {
  Body?: string;
  Preheader?: string;
  "Video CTA"?: string;
  Introduction?: string;
  "Subject Line"?: string;
  "Closing and Final CTA"?: string;
  "Objections and Reassurance"?: string;
};

export type ReminderEmail = GenericEmail;
export type ReminderEmailResponse = BaseApiResponseData<{
  project_id: number;
  email_reminder_generated: ReminderEmail;
}>;

export type PainPointsEmail = GenericEmailWithPreheader;
export type PainPointsEmailResponse = BaseApiResponseData<{
  project_id: number;
  email_painpoints_generated: PainPointsEmail;
}>;

export type UseCaseEmail = GenericEmailWithPreheader;
export type UseCaseEmailResponse = BaseApiResponseData<{
  project_id: number;
  email_usecase_generated: UseCaseEmail;
}>;

export type UrgencyEmail = GenericEmailWithPreheader;
export type UrgencyEmailResponse = BaseApiResponseData<{
  project_id: number;
  email_urgency_generated: UrgencyEmail;
}>;

export type OfferEmail = GenericEmailWithPreheader;
export type OfferEmailResponse = BaseApiResponseData<{
  project_id: number;
  email_offer_generated: OfferEmail;
}>;

export function createEmailAPI<
  T extends BaseApiResponseData<any>,
  K extends any,
>(pathName: string, fieldName: keyof T["data"]) {
  return {
    fieldName,
    async get(projectId: number | string): Promise<T> {
      try {
        const response = await $api<T>(
          `/v1/application/hiluca/project/${projectId}/email/${pathName}`,
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

    async generate(projectId: number | string): Promise<T> {
      try {
        const response = await $api<T>(
          `/v1/application/hiluca/project/email/${pathName}/generate`,
          {
            method: "POST",
            body: {
              project_id: projectId,
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

    async save(projectId: number | string, data: K): Promise<T> {
      try {
        const response = await $api<T>(
          `/v1/application/hiluca/project/email/${pathName}`,
          {
            method: "POST",
            body: {
              project_id: projectId,
              [fieldName]: data,
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

    async getOrGenerate(projectId: number | string) {
      // Try to get the email
      let response = await this.get(projectId);

      // If it's empty, generate the emails
      if (Object.keys(response.data[fieldName]).length === 0) {
        response = await this.generate(projectId);
      }

      return response;
    },
  };
}

const Reminder = createEmailAPI<ReminderEmailResponse, ReminderEmail>(
  "reminder",
  "email_reminder_generated",
);

const PainPoints = createEmailAPI<PainPointsEmailResponse, PainPointsEmail>(
  "painpoints",
  "email_painpoints_generated",
);

const UseCase = createEmailAPI<UseCaseEmailResponse, UseCaseEmail>(
  "usecase",
  "email_usecase_generated",
);

const Urgency = createEmailAPI<UrgencyEmailResponse, UrgencyEmail>(
  "urgency",
  "email_urgency_generated",
);

const Offer = createEmailAPI<OfferEmailResponse, OfferEmail>(
  "offer",
  "email_offer_generated",
);

export default { Reminder, PainPoints, UseCase, Urgency, Offer };
