export type Targeting = {
  geo_locations?: {
    countries?: string[];
    country_groups?: string[];
  };
  age_min: number | null;
  age_max: number | null;
  genders: number[] | null;
  interests?: { id: string; name: string }[] | null;
};

export type AdImage = {
  image_url: string;
};

export type ObjectStorySpecLinkData = {
  link: string;
};

export type ObjectStorySpec = {
  page_id: string;
};

export type AssetFeedSpec = {
  images: { url?: string; hash?: string }[];
  bodies: { text: string }[];
  titles: { text: string }[];
  descriptions: { text: string }[];
  call_to_action_types: string[];
  ad_formats: string[];
};

export type AdCreative = {
  id: string;
  name: string;
  ad_account_id: string;
  object_story_spec: ObjectStorySpec;
  asset_feed_spec: AssetFeedSpec | null;
  creative_asset_groups: CreativeAssetGroup[] | null;
  ad_image: AdImage | null;
};

export type CreativeAssetGroupsSpec = {
  creative_asset_groups: CreativeAssetGroup[] | null;
};

export type CreativeAssetGroup = {
  image_hash: string;
  titles: [{ text: string }];
  bodies: [{ text: string }];
  descriptions: [{ text: string }];
  call_to_action_type: string;
};

export type Ad = {
  id: string;
  name: string;
  ad_account_id: string;
  adset_id: string;
  adCreative: AdCreative | null;
  creative: { creative_id: string };
  status: string;
};

export type AdSet = {
  id: string;
  name: string;
  campaign_id: string;
  ad_account_id: string;
  daily_budget: string;
  billing_event: string;
  optimization_goal: string;
  targeting: Targeting;
  status: string;
  ads: Ad[];
};

export type Campaign = {
  id: string;
  name: string;
  ad_account_id: string;
  objective: string;
  status: string;
  buying_type: string;
  special_ad_categories: string[];
  adSets: AdSet[];
};

export const metaAdsConnectionStore = defineStore("metaAdsConnection", {
  state: () => ({
    campaign: {
      id: "",
      name: "",
      ad_account_id: "",
      objective: "OUTCOME_AWARENESS",
      status: "PAUSED",
      buying_type: "AUCTION",
      special_ad_categories: [],
      adSets: [],
    } as Campaign,

    selectedPageId: "",
  }),

  getters: {
    metaPayload(state) {
      return {
        connection: "google-ads",
        campaign: {
          name: state.campaign.name,
          objective: state.campaign.objective,
          status: state.campaign.status,
          buying_type: state.campaign.buying_type,
          special_ad_categories: state.campaign.special_ad_categories,
          ad_account_id: state.campaign.ad_account_id,
        },
        adsets: state.campaign.adSets.map((set) => ({
          name: set.name,
          daily_budget: set.daily_budget,
          billing_event: set.billing_event,
          optimization_goal: set.optimization_goal,
          targeting: set.targeting,
          status: set.status,
          ad_account_id: set.ad_account_id,
          campaign_id: set.campaign_id,
          ads: set.ads.map((ad) => ({
            name: ad.name,
            ad_account_id: ad.ad_account_id,
            adCreative: ad.adCreative,
            asset_feed_spec: null,
            status: ad.status,
          })),
        })),
      };
    },
  },

  actions: {
    setCampaign(data: Partial<Campaign>) {
      this.campaign = { ...this.campaign, ...data };
    },

    setCampaignObjective(objective: string) {
      this.campaign.objective = objective;
    },

    setOptimizationGoal(adSetIndex: number, goal: string) {
      this.campaign.adSets[adSetIndex].optimization_goal = goal;
    },

    setAdAccountId(adAccountId: string) {
      this.campaign.ad_account_id = adAccountId;
      this.campaign.adSets.forEach((set) => {
        set.ad_account_id = adAccountId;
        set.ads.forEach((ad) => (ad.ad_account_id = adAccountId));
        set.ads.forEach((ad) => {
          ad.adCreative!.ad_account_id = adAccountId;
        });
      });
    },

    setPageId(pageId: string) {
      this.selectedPageId = pageId;
      this.campaign.adSets.forEach((set) => {
        set.ads.forEach((ad) => {
          ad.adCreative!.object_story_spec.page_id = pageId;
        });
      });
    },

    setAdSets(adSets: AdSet[]) {
      this.campaign.adSets = adSets;
    },

    updateAdSet(adSetIndex: number, data: Partial<AdSet>) {
      Object.assign(this.campaign.adSets[adSetIndex], data);
    },

    addAd(adSetIndex: number, data: Partial<Ad>) {
      const adSet = this.campaign.adSets[adSetIndex];
      const newAd: Ad = {
        id: "",
        name: data.name || "",
        ad_account_id: this.campaign.ad_account_id,
        adset_id: adSet.id,
        creative: { creative_id: "" },
        adCreative: data.adCreative || {
          id: "",
          name: "",
          ad_account_id: this.campaign.ad_account_id,
          object_story_spec: {
            page_id: this.selectedPageId,
          },
          ad_image: null,
          asset_feed_spec: null,
          creative_asset_groups: [],
        },
        status: data.status || "PAUSED",
      };
      adSet.ads.push(newAd);
    },

    setAdImage(adSetIndex: number, adIndex: number, image: { url?: string }) {
      const ad = this.campaign.adSets[adSetIndex].ads[adIndex];

      if (!ad.adCreative!.asset_feed_spec) {
        ad.adCreative!.asset_feed_spec = {
          images: [],
          bodies: [],
          titles: [],
          descriptions: [],
          call_to_action_types: [],
          ad_formats: [],
        };
      }

      if (image.url) {
        ad.adCreative!.asset_feed_spec!.images.push({ url: image.url });
      }
    },

    setTargeting(adSetIndex: number, targeting: Targeting) {
      this.campaign.adSets[adSetIndex].targeting = targeting;
    },

    setCampaignName(name: string) {
      this.campaign.name = name;
    },

    setAssetFeedSpec(
      adSetIndex: number,
      adIndex: number,
      assetFeedSpec: AssetFeedSpec,
    ) {
      const ad = this.campaign.adSets[adSetIndex].ads[adIndex];
      ad.adCreative!.asset_feed_spec = assetFeedSpec;
    },

    setCreativeAssetGroupsSpec(
      adSetIndex: number,
      adIndex: number,
      creativeAssetGroupsSpec: CreativeAssetGroup[],
    ) {
      const ad = this.campaign.adSets[adSetIndex].ads[adIndex];
      ad.adCreative!.creative_asset_groups = creativeAssetGroupsSpec;
    },

    setDailyBudget(adSetIndex: number, dailyBudget: string) {
      this.campaign.adSets[adSetIndex].daily_budget = dailyBudget;
    },
  },
});
