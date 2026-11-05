import { defineStore } from "pinia";

export enum CampaignObjective {
  SALES = "SALES",
  LEADS = "LEADS",
  WEBSITE_TRAFFIC = "WEBSITE_TRAFFIC",
  BRAND_AWARENESS_AND_REACH = "BRAND_AWARENESS_AND_REACH",
  PRODUCT_AND_BRAND_CONSIDERATION = "PRODUCT_AND_BRAND_CONSIDERATION",
  APP_PROMOTION = "APP_PROMOTION",
  LOCAL = "LOCAL",
  UNSPECIFIED = "UNSPECIFIED",
}

export enum CampaignChannelType {
  SEARCH = "SEARCH",
  DISPLAY = "DISPLAY",
  VIDEO = "VIDEO",
  PERFORMANCE_MAX = "PERFORMANCE_MAX",
  SHOPPING = "SHOPPING",
  LOCAL = "LOCAL",
  DISCOVERY = "DISCOVERY",
}

export enum AdGroupStatus {
  ENABLED = "ENABLED",
  PAUSED = "PAUSED",
  REMOVED = "REMOVED",
}

export enum DeliveryMethod {
  STANDARD = "STANDARD",
  ACCELERATED = "ACCELERATED",
}

export enum CampaignStatus {
  ENABLED = "ENABLED",
  PAUSED = "PAUSED",
  REMOVED = "REMOVED",
}

export interface Budget {
  name: string;
  amount_micros: number;
  delivery_method: string;
}

export interface AdTextAsset {
  text: string;
}

export interface AdData {
  headlines: string[];
  descriptions: string[];
  final_urls: string[];
  image_urls?: string[];
}

export interface AdGroup {
  name: string;
  status: AdGroupStatus;
  ads: AdData[];
}

export interface GoogleCampaign {
  name: string;
  channel_type: CampaignChannelType;
  status: string;
  objective: CampaignObjective;
}

export interface GoogleAdsConnectionState {
  budget: Budget;
  campaign: GoogleCampaign;
  ad_groups: AdGroup[];
  customerId: string | null;
}

export const googleAdsConnectionStore = defineStore("googleAdsConnection", {
  state: (): GoogleAdsConnectionState => ({
    budget: {
      name: "",
      amount_micros: 50000000,
      delivery_method: DeliveryMethod.STANDARD,
    },
    campaign: {
      name: "",
      channel_type: CampaignChannelType.SEARCH,
      status: CampaignStatus.PAUSED,
      objective: CampaignObjective.UNSPECIFIED,
    },
    ad_groups: [],
    customerId: null,
  }),

  getters: {
    googlePayload(state) {
      return {
        budget: state.budget,
        campaign: state.campaign,
        ad_groups: state.ad_groups,
      };
    },
  },

  actions: {
    setCustomerId(customerId: string) {
      this.customerId = customerId;
    },

    setAdGroups(adGroups: AdGroup[]) {
      this.ad_groups = adGroups;
    },

    setCampaignObjective(objective: CampaignObjective) {
      this.campaign.objective = objective;
    },

    setCampaignName(name: string) {
      this.campaign.name = name;
    },

    setBudgetName(campaignName: string, customerId: string) {
      this.budget.name = `Budget - ${campaignName} - ${customerId}`;
    },

    setAdgroupsName(adSetIndex, name: string) {
      this.ad_groups[adSetIndex].name = name;
      this.ad_groups[adSetIndex].status = AdGroupStatus.PAUSED;
    },

    setAdsData(adSetIndex, adIndex, ad: AdData) {
      this.ad_groups[adSetIndex].ads[adIndex] = ad;
    },

    setChannelType(channel: CampaignChannelType) {
      this.campaign.channel_type = channel;
    },
  },
});
