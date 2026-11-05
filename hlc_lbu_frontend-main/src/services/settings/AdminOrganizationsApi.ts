import { AdminUserRole } from "./AdminRolesApi";
import { handleCommonErrors } from "../common-errors";
import type { BaseApiResponseData } from "@/utils/type-declarations";

export type AdminOrganization = {
  id: string;
  account: string;
  status: "P" | "A" | "I";
  roles: AdminUserRole[];
  extra_info: {
    first_name: string;
    last_name: string;
    fullname: string;
  };
};

export type AdminOrganizationListResponse =
  BaseApiPaginatedResponseData<AdminOrganization>;

export type AdminOrganizationCreationBody = {
  email: string;
  first_name: string;
  last_name: string;
  roles: number[];
};

export class AdminOrganizationEmailIsRegistered extends Error {
  constructor() {
    super("ADMIN_ORGANIZATION_EMAIL_IS_REGISTERED");
    this.name = this.constructor.name;
  }
}

export default {
  async getList({
    range,
    filter,
  }: {
    range?: [number, number];
    filter?: { account?: string; status?: string };
  } = {}): Promise<AdminOrganizationListResponse> {
    try {
      const params = new URLSearchParams();
      if (range) params.append("range", JSON.stringify(range));
      if (filter) params.append("filter", JSON.stringify(filter));

      const url = `/v1/admin/organization?${params.toString()}`;
      return await $api<AdminOrganizationListResponse>(url, { method: "GET" });
    } catch (error: unknown) {
      handleCommonErrors(error as BaseApiResponseData<unknown>);
      throw error;
    }
  },

  async create(
    body: AdminOrganizationCreationBody,
  ): Promise<AdminOrganization> {
    try {
      return await $api<AdminOrganization>("/v1/admin/organization", {
        body,
        method: "POST",
      });
    } catch (error: any) {
      const message = error.message?.text;

      if (message === "Email is Registered!") {
        throw new AdminOrganizationEmailIsRegistered();
      }

      handleCommonErrors(error);
      throw error;
    }
  },

  async update(
    body: AdminOrganizationCreationBody,
  ): Promise<AdminOrganization> {
    try {
      return await $api<AdminOrganization>("/v1/admin/organization", {
        body,
        method: "PUT",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async delete(email: string): Promise<AdminOrganization> {
    try {
      return await $api<AdminOrganization>(`/v1/admin/organization/${email}`, {
        method: "DELETE",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async sendInvitation(body: { email: string }): Promise<AdminOrganization> {
    try {
      return await $api<AdminOrganization>("/v1/admin/organization/invite", {
        body,
        method: "POST",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async reactivate(body: { email: string }): Promise<AdminOrganization> {
    try {
      return await $api<AdminOrganization>(
        `/v1/admin/organization/${body.email}`,
        {
          body,
          method: "PUT",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
