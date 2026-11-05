import { ofetch } from "ofetch";
import { BaseApiResponseData } from "@/utils/type-declarations";
import { handleCommonErrors } from "../common-errors";
import { Country } from "../projects/AudienceApi";

export type AdAccount = {
  id: string;
  account_id: string;
  name: string;
  currency?: string;
  account_currency?: string;
  account_status: number;
  timezone_name: string;
};

export type GoogleAdsCustomer = {
  customers: {
    id: string;
    name: string;
  }[];
};

export type AdPage = {
  id: string;
  name: string;
};

export type FacebookValidateTokenResponse = {
  is_valid: boolean;
};

export type WhatsAppPhoneNumber = {
  id: string;
  display_phone_number: string;
  verified_name: string;
  code_verification_status: string;
  quality_rating: string;
  platform_type: string;
  throughput: {
    level: string;
  };
};

export type FacebookResetAuthResponse = {
  message: string;
};

export type LocationMetaAds = {
  key: string;
  country_code: string;
};

export type InterestMetaAds = {
  id: string;
  name: string;
};

export type MinimumBudget = {
  currency: string;
  min_daily_budget_imp: number;
};

export type CompleteCampaignData = {
  ad_account_id: string;
  page_id: string;
  objective: string;
  optimization_goal: string;
  lead_gen_form_id?: string | null;
};

export type LaunchPreCheckRequest = {
  brand_id: number;
  campaign_id: number;
  ad_account_id: string;
  page_id: string;
  objective: string;
  optimization_goal: string;
  creative_type: string;
  daily_budget: number | null;
  lead_gen_form_id?: string | null;
  whatsapp_number_id?: string | null;
  /**
   * Required when `objective` is `OUTCOME_SALES`, or `OUTCOME_LEADS` with the
   * `OFFSITE_CONVERSIONS` goal.
   */
  pixel_id?: string | null;
  /** Required for `OUTCOME_LEADS` with the `OFFSITE_CONVERSIONS` goal. */
  conversion_event?: LeadsConversionEvent | null;
};

// Conversion events accepted by the back-end for `OUTCOME_LEADS` with the
// `OFFSITE_CONVERSIONS` goal
export const LEADS_CONVERSION_EVENTS = [
  "COMPLETE_REGISTRATION",
  "LEAD",
  "CONTACT",
  "SUBMIT_APPLICATION",
  "SCHEDULE",
  "SUBSCRIBE",
  "START_TRIAL",
] as const;

export type LeadsConversionEvent = (typeof LEADS_CONVERSION_EVENTS)[number];

export type FacebookAdPixel = {
  id: string;
  name: string;
};

export type LaunchPreCheckCampaign = {
  name: string;
  channel_name: string;
  creatives_no: number;
  objective: string;
  optimization_goal: string;
  mode: string;
  // Only returned by the published campaign endpoint
  conversion_event?: LeadsConversionEvent | null;
};

export type LaunchPreCheckTextItem = {
  text: string;
  valid_length: boolean;
};

export type LaunchPreCheckCallToAction = {
  value: string;
  valid: boolean;
};

export type LaunchPreCheckLocation = {
  key: string;
  name: string;
  type: "city" | "region" | "country";
  country_code: string;
  country_name: string;
  region?: string;
  region_id?: number;
  supports_region: boolean;
  supports_city: boolean;
};

export type LaunchPreCheckCreative = {
  idx: number;
  name: string;
  adset_id: number;
  ad_id: number;
  adchannel_id: number;
  daily_budget: number;
  targeting: {
    geo_locations: {
      country_groups: string[];
    };
    age_min: number;
    age_max: number;
    genders: number[];
    interests: string[] | null;
  };
  images: Array<{
    url: string;
    valid: boolean;
    error: string;
  }>;
  bodies: LaunchPreCheckTextItem[];
  titles: LaunchPreCheckTextItem[];
  descriptions: LaunchPreCheckTextItem[];
  call_to_action_types: LaunchPreCheckCallToAction[];
  images_valid_amount: boolean;
  titles_valid_amount: boolean;
  bodies_valid_amount: boolean;
  descriptions_valid_amount: boolean;
  call_to_action_types_valid_amount: boolean;
  images_max_amount: number;
  titles_max_amount: number;
  bodies_max_amount: number;
  descriptions_max_amount: number;
  call_to_action_types_max_amount: number;
  unique_titles: boolean;
  unique_bodies: boolean;
  unique_descriptions: boolean;
  daily_budget_valid: boolean;
  min_daily_budget: number;
  proposal_url: string;
  proposal_url_valid: boolean;
  proposal_locations: Country[] | string[];
  locations: LaunchPreCheckLocation[];
  locations_valid: boolean;
};

export type LaunchPreCheckData = {
  campaign: LaunchPreCheckCampaign;
  creatives: LaunchPreCheckCreative[];
  // Not returned by the published campaign endpoint
  valid_ctas?: string[];
  account_config?: {
    currency: string;
  };
};

export type LaunchPreCheckResponse = BaseApiResponseData<LaunchPreCheckData>;

// Same payload as the pre-check plus the Meta Ads link of the published campaign
export type LaunchPublishedData = LaunchPreCheckData & {
  meta_url: string;
};

export type LaunchPublishedResponse = BaseApiResponseData<LaunchPublishedData>;

export type PreCheckTextsRequest = {
  brand_id: number;
  campaign_id: number;
  adset_id: number;
  ad_id: number;
  adchannel_id: number;
  bodies: LaunchPreCheckTextItem[];
  titles: LaunchPreCheckTextItem[];
  descriptions: LaunchPreCheckTextItem[];
};

export type PreCheckTextsResponse = BaseApiResponseData<LaunchPreCheckCreative>;

export type LaunchPreCheckImageItem = {
  url: string;
  valid: boolean;
  error: string;
};

export type PreCheckImagesRequest = {
  brand_id: number;
  campaign_id: number;
  adset_id: number;
  ad_id: number;
  adchannel_id: number;
  images: LaunchPreCheckImageItem[];
};

export type PreCheckImagesResponse =
  BaseApiResponseData<LaunchPreCheckCreative>;

export type PreCheckBudgetRequest = {
  brand_id: number;
  campaign_id: number;
  adset_id: number;
  ad_id: number;
  adchannel_id: number;
  daily_budget: number;
};

export type PreCheckBudgetResponse =
  BaseApiResponseData<LaunchPreCheckCreative>;

export type PreCheckCTAsRequest = {
  brand_id: number;
  campaign_id: number;
  adset_id: number;
  ad_id: number;
  adchannel_id: number;
  call_to_action_types: LaunchPreCheckCallToAction[];
};

export type PreCheckCTAsResponse = BaseApiResponseData<LaunchPreCheckCreative>;

export type PreCheckProposalUrlRequest = {
  brand_id: number;
  campaign_id: number;
  adset_id: number;
  ad_id: number;
  adchannel_id: number;
  proposal_url: string;
};

export type PreCheckProposalUrlResponse =
  BaseApiResponseData<LaunchPreCheckCreative>;

export type PreCheckLocationsRequest = {
  brand_id: number;
  campaign_id: number;
  adset_id: number;
  ad_id: number;
  adchannel_id: number;
  locations: LaunchPreCheckLocation[];
};

export type PreCheckLocationsResponse =
  BaseApiResponseData<LaunchPreCheckCreative>;

export type LaunchPublishRequest = {
  brand_id: number;
  campaign_id: number;
  creatives: Array<{
    adset_id: number;
    ad_id: number;
    adchannel_id: number;
  }>;
};

// For some reason, the backend returns the creatives with the images/targeting/etc. as null
export type LaunchPublishData = {
  campaign: LaunchPreCheckCampaign;
  creatives: LaunchPreCheckCreative[];
  meta_url: string;
};

export type LaunchPublishJobResponse = BaseApiResponseData<{ job_id: string }>;

export type LaunchPublishTaskValue =
  | {
      ok: 1;
      data: LaunchPublishData;
    }
  | {
      ok: 0;
      message?: {
        text?: {
          error?: {
            error_user_title?: string;
            error_user_msg?: string;
          };
        };
      };
    };

export type LaunchExportAssetsRequest = {
  brand_id: number;
  campaign_id: number;
  adset_id: number;
  ad_id: number;
  adchannel_id: number;
};

export type CampaignObjectiveGoal = {
  id: string;
  billing_event: string;
};

export type CampaignObjective = {
  id: string;
  active: boolean;
  goals: CampaignObjectiveGoal[];
};

export type CampaignObjectivesResponse = BaseApiResponseData<
  CampaignObjective[]
>;

export type MetaInsightsLevel = "account" | "campaign" | "adset" | "ad";

export type MetaInsightsParams = {
  fields?: string;
  level?: MetaInsightsLevel;
  date_preset?: string;
  time_increment?: string;
  time_range?: string;
};

export type MetaInsightAction = {
  action_type?: string;
  value?: string;
};

export type MetaCampaignInsight = {
  campaign_id?: string;
  campaign_name?: string;
  account_id?: string;
  account_currency?: string;
  impressions?: string;
  reach?: string;
  spend?: string;
  clicks?: string;
  conversions?: MetaInsightAction[];
  ctr?: string;
  cpc?: string;
  date_start?: string;
  date_stop?: string;
};

export type MetaInsightsResponse = {
  data: MetaCampaignInsight[];
  paging?: {
    cursors?: {
      before?: string;
      after?: string;
    };
    next?: string;
    previous?: string;
  };
};

export default {
  async validateFacebookToken() {
    try {
      return await $api<FacebookValidateTokenResponse>(
        "/v2/external/facebook/validate_token",
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async disconnectFacebookToken() {
    try {
      return await $api<FacebookResetAuthResponse>(
        "/v2/external/facebook/reset_auth",
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getMinimumBudget(adAccountId: string) {
    try {
      return await $api<BaseApiResponseData<MinimumBudget[]>>(
        `/v2/external/facebook/minimum_budget/${adAccountId}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getCustomersListInfo(adAccountId: string) {
    try {
      return await $api<GoogleAdsCustomer>(
        `/v2/external/google-ads/list-customers/${adAccountId}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getAdAccountInfo(adAccountId: string) {
    try {
      return await $api<AdAccount>(
        `/v2/external/facebook/ad_account/${adAccountId}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async searchMeta<T extends LocationMetaAds | InterestMetaAds>(
    type: string,
    query: string,
    location_types: string[],
  ) {
    try {
      return await $api<BaseApiResponseData<T[]>>(
        "/v2/external/facebook/search",
        {
          method: "GET",
          params: {
            type,
            q: query,
            location_types,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async searchMetaLocations(query: string): Promise<LaunchPreCheckLocation[]> {
    try {
      const response = await $api<
        BaseApiResponseData<LaunchPreCheckLocation[]>
      >("/v2/external/facebook/search", {
        method: "GET",
        params: {
          type: "adgeolocation",
          q: query,
          location_types: `["country", "region", "city"]`,
        },
      });

      return response.data;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getAdAccounts() {
    try {
      return await $api<BaseApiResponseData<AdAccount[]>>(
        "/v2/external/facebook/ad_accounts",
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getAdPages() {
    try {
      return await $api<BaseApiResponseData<AdPage[]>>(
        "/v2/external/facebook/pages",
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getLeadgenForms(pageId: string) {
    try {
      return await $api<BaseApiResponseData<any[]>>(
        `/v2/external/facebook/pages/${pageId}/leadgen_forms`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getAdsPosts(pageId: string) {
    try {
      return await $api<BaseApiResponseData<any[]>>(
        `/v2/external/facebook/pages/${pageId}/ads_posts`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getWhatsAppPhoneNumbers(pageId: string) {
    try {
      return await $api<BaseApiResponseData<WhatsAppPhoneNumber[]>>(
        `/v2/external/facebook/pages/${pageId}/whatsapp_numbers`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getPixelsByAccount(adAccountId: string) {
    try {
      return await $api<BaseApiResponseData<FacebookAdPixel[]>>(
        `/v2/external/facebook/ad_account/${adAccountId}/pixels`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getInsights(adAccountId: string, params?: MetaInsightsParams) {
    try {
      return await $api<MetaInsightsResponse>(
        `/v2/external/facebook/insights/ad_account/${adAccountId}`,
        {
          method: "GET",
          params,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async getInsightsByNextUrl(nextUrl: string) {
    try {
      return await ofetch<MetaInsightsResponse>(nextUrl);
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async UploadCampaign(
    campaignId: string,
    completeCampaignData?: CompleteCampaignData,
    creativeType?: string,
  ) {
    try {
      return await $api<any>(
        `/v2/external/facebook/publish_campaign/${campaignId}`,
        {
          method: "POST",
          body: {
            complete_campaign_data: completeCampaignData,
            creative_type: creativeType,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async testUploadCreatives(
    campaignId: string,
    completeCampaignData?: CompleteCampaignData,
    creativeType?: string,
  ) {
    try {
      return await $api<any>(
        `/v2/external/facebook/upload_creatives/${campaignId}`,
        {
          method: "POST",
          body: {
            complete_campaign_data: completeCampaignData,
            creative_type: creativeType,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async testStrapiGetCampaign(
    campaignId: string,
    brandId?: number,
    channelGroupId?: number,
    userId?: string,
  ) {
    try {
      return await $api<any>(
        `/v2/application/hiluca/test/strapi/campaign/${campaignId}`,
        {
          method: "GET",
          params: {
            brand_id: brandId,
            channel_group_id: channelGroupId,
            user_id: userId,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async generateLaunchPreCheck(data: LaunchPreCheckRequest) {
    try {
      return await $api<LaunchPreCheckResponse>(
        "/v2/external/facebook/launch/pre_check",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async saveAndValidatePreCheckTexts(data: PreCheckTextsRequest) {
    try {
      return await $api<PreCheckTextsResponse>(
        "/v2/external/facebook/launch/pre_check/texts",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async saveAndValidatePreCheckImages(data: PreCheckImagesRequest) {
    try {
      return await $api<PreCheckImagesResponse>(
        "/v2/external/facebook/launch/pre_check/images",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async saveAndValidatePreCheckBudget(data: PreCheckBudgetRequest) {
    try {
      return await $api<PreCheckBudgetResponse>(
        "/v2/external/facebook/launch/pre_check/budget",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      // Check for DAT001 error before handleCommonErrors transforms it
      const errorCode =
        error?.response?.data?.message?.code ||
        error?.data?.message?.code ||
        error?.message?.code;
      if (errorCode === "DAT001") {
        // Re-throw with original structure so component can handle it
        throw error;
      }
      handleCommonErrors(error);
      throw error;
    }
  },
  async saveAndValidatePreCheckCTAs(data: PreCheckCTAsRequest) {
    try {
      return await $api<PreCheckCTAsResponse>(
        "/v2/external/facebook/launch/pre_check/ctas",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async saveAndValidatePreCheckProposalUrl(data: PreCheckProposalUrlRequest) {
    try {
      return await $api<PreCheckProposalUrlResponse>(
        "/v2/external/facebook/launch/pre_check/proposal_url",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async saveAndValidatePreCheckLocations(data: PreCheckLocationsRequest) {
    try {
      return await $api<PreCheckLocationsResponse>(
        "/v2/external/facebook/launch/pre_check/locations",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
  async publishLaunchToMeta(data: LaunchPublishRequest) {
    try {
      return await $api<LaunchPublishJobResponse>(
        "/v2/external/facebook/launch/publish",
        {
          method: "POST",
          body: data,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);

      // We need to re-throw the error because it could be a Meta error that needs to be handled
      throw error;
    }
  },
  /**
   * Returns the pre-check info of an already published campaign, or
   * `undefined` when the campaign has not been published yet (the back-end
   * answers with a `DAT001` error in that case).
   */
  async getPublishedLaunch(brandId: number, campaignId: number) {
    try {
      return await $api<LaunchPublishedResponse>(
        `/v2/external/facebook/launch/publish/brand/${brandId}/campaign/${campaignId}`,
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      const errorCode =
        error?.response?.data?.message?.code ||
        error?.data?.message?.code ||
        error?.message?.code;

      // The campaign has not been published yet
      if (errorCode === "DAT001") {
        return undefined;
      }

      console.error("Failed to get the published campaign:", error);
      handleCommonErrors(error);
      throw error;
    }
  },
  async exportLaunchAssets(data: LaunchExportAssetsRequest) {
    try {
      return await $api<Blob>(
        "/v2/external/facebook/launch/publish/export_assets",
        {
          method: "POST",
          body: data,
          responseType: "blob" as any,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getCampaignObjectives() {
    try {
      return await $api<CampaignObjectivesResponse>(
        "/v2/external/facebook/campaign_objective",
        {
          method: "GET",
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
