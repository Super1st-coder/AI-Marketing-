import { handleCommonErrors, PermissionError } from "../common-errors";
import type { BaseApiResponseData } from "@/utils/type-declarations";

export type AdminRole = {
  id: number;
  name: string;
  icon: string;
  status: "A";
};

export type AdminRoleListResponse = BaseApiResponseData<AdminRole[]> & {
  count: number;
  total: number;
};

export type AdminRoleAction = {
  id: string;
  name: string;
};

export type AdminRoleFunction = {
  id: number;
  name: PermissionFunctionName;
  long_name: string;
  status: string;
  actions: AdminRoleAction[];
};

export type AdminRoleDetail = {
  id: number;
  name: string;
  icon: string;
  status: string;
  functions: AdminRoleFunction[];
};

export type AdminRoleDetailResponse = BaseApiResponseData<AdminRoleDetail>;

export type AdminUserRole = {
  id: number;
  name: string;
};

export type AdminUser = {
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

export type AdminUserListResponse = BaseApiPaginatedResponseData<AdminUser>;

export type AdminUserCreationBody = {
  email: string;
  first_name: string;
  last_name: string;
  roles: number[];
};

export class AdminUserEmailIsRegistered extends Error {
  constructor() {
    super("ADMIN_USER_EMAIL_IS_REGISTERED");
    this.name = this.constructor.name;
  }
}

export default {
  async getList(): Promise<AdminRoleListResponse> {
    try {
      return await $api<AdminRoleListResponse>("/v1/admin/role", {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getOne(roleId: number): Promise<AdminRoleDetailResponse> {
    try {
      return await $api<AdminRoleDetailResponse>(`/v1/admin/role/${roleId}`, {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getUserList({
    range,
    filter,
  }: {
    range?: [number, number];
    filter?: { account?: string; status?: string };
  } = {}): Promise<AdminUserListResponse> {
    try {
      const params = new URLSearchParams();
      if (range) params.append("range", JSON.stringify(range));
      if (filter) params.append("filter", JSON.stringify(filter));

      const url = `/v1/admin/member?${params.toString()}`;
      return await $api<AdminUserListResponse>(url, { method: "GET" });
    } catch (error: unknown) {
      handleCommonErrors(error as BaseApiResponseData<unknown>);
      throw error;
    }
  },

  async addUser(body: AdminUserCreationBody): Promise<AdminUser> {
    try {
      return await $api<AdminUser>("/v1/admin/member", {
        body,
        method: "POST",
      });
    } catch (error: any) {
      const message = error.message?.text;
      const code = error.message?.code;

      if (message === "Email is Registered!") {
        throw new AdminUserEmailIsRegistered();
      }

      if (code === "N8N001") {
        throw new PermissionError();
      }

      handleCommonErrors(error);
      throw error;
    }
  },

  async updateUser(body: AdminUserCreationBody): Promise<AdminUser> {
    try {
      return await $api<AdminUser>("/v1/admin/member", {
        body,
        method: "PUT",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async deleteUser(email: string): Promise<AdminUser> {
    try {
      return await $api<AdminUser>(`/v1/admin/member/${email}`, {
        method: "DELETE",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async sendUserInvitation(body: { email: string }): Promise<AdminUser> {
    try {
      return await $api<AdminUser>("/v1/admin/member/invite", {
        body,
        method: "POST",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
