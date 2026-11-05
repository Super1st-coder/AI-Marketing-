import { handleCommonErrors } from "../common-errors";
import { $lucaGuideApi } from "@/utils/api";

export type LucaGuideFacebookOAuthStatus = {
  configured: boolean;
  connected: boolean;
  token_expired: boolean;
  token_expires_at: string | null;
  account_id: string | null;
};

export type LucaGuideFacebookLoginUrl = {
  configured: boolean;
  login_url: string;
};

export default {
  async getFacebookStatus(): Promise<LucaGuideFacebookOAuthStatus> {
    try {
      return await $lucaGuideApi<LucaGuideFacebookOAuthStatus>(
        "/api/v2/oauth/facebook/status",
        {
          method: "GET",
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },

  async getFacebookLoginUrl(
    returnTo?: string,
  ): Promise<LucaGuideFacebookLoginUrl> {
    try {
      return await $lucaGuideApi<LucaGuideFacebookLoginUrl>(
        "/api/v2/oauth/facebook/login-url",
        {
          method: "GET",
          params: returnTo ? { return_to: returnTo } : undefined,
        },
      );
    } catch (error) {
      handleCommonErrors(error as any);
      throw error;
    }
  },
};
