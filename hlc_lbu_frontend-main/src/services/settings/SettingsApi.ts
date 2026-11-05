import { handleCommonErrors } from "../common-errors";

export default {
  async updatePassword(
    old_password: string,
    new_password: string,
  ): Promise<Response> {
    try {
      return await $api<Response>("/v1/member/password", {
        method: "PUT",
        body: {
          old_password,
          new_password,
        },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
