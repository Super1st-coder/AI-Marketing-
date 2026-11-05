<script setup lang="ts">
import { FunnelPaidSocialFormData } from "../../FunnelPaidSocialForm.vue";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";

const metaAdsConnection = metaAdsConnectionStore();
const adsConnection = adsConnectionStore();
const googleAdsConnection = googleAdsConnectionStore();

const { goNext, currentFlatStepIndex, goToStep, goBack } =
  useMultiStepFormContext();

const { data } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const brandId = useBrandId();
const campaignId = useCampaignId();
const authStore = useAuthStore();
const googleAdsAuth = googleAdsAuthStore();

const { data: adStructure } = await AdStructureApi.getAdStructureByChannelGroup(
  brandId,
  campaignId,
  data.value.channelGroupId,
);

const appId = "461281100028116";
const redirectUri = `${window.location.origin}/facebook-auth-callback`;
const scope =
  "email,public_profile,pages_show_list,ads_management,business_management";

async function authWithFacebook(objective: string) {
  const data = await $api("/v2/external/facebook/validate_token");

  const width = 1024;
  const height = 780;
  const left = window.screenX + (window.outerWidth - width) / 2;
  const top = window.screenY + (window.outerHeight - height) / 2;

  const adSets: AdSet[] = adStructure.ad_sets.flatMap((adSet) =>
    adSet.ads.map((ad) => ({
      id: `${adSet.id || ""}_${ad.id || ""}`,
      name: `${adSet.name} - ${ad.name}`,
      campaign_id: "",
      ad_account_id: "",
      daily_budget: "100",
      billing_event: "IMPRESSIONS",
      optimization_goal: objective,
      targeting: {
        geo_locations: { countries: [] },
        age_min: null,
        age_max: null,
        genders: null,
        interests: null,
      },
      status: "PAUSED",
      ads: [
        {
          id: ad.id?.toString() || "",
          name: ad.name,
          ad_account_id: "",
          asset_feed_spec: null,
          adset_id: `${adSet.id || ""}_${ad.id || ""}`,
          creative: { creative_id: "" },
          adCreative: {
            id: "",
            name: `${ad.name}_creative`,
            ad_account_id: "",
            ad_image: null,
            object_story_spec: {
              page_id: "",
            },
            asset_feed_spec: null,
            creative_asset_groups: [],
            creative_asset_groups_spec: {
              creative_asset_groups: [],
            },
          },
          status: "PAUSED",
        },
      ],
    })),
  );

  metaAdsConnection.setAdSets(adSets);

  if (!data.is_valid) {
    window.open(
      `https://www.facebook.com/v20.0/dialog/oauth?client_id=${appId}&redirect_uri=${encodeURIComponent(
        redirectUri,
      )}&scope=${scope}&response_type=code`,
      "facebookLogin",
      `width=${width},height=${height},left=${left},top=${top}`,
    );

    const checkToken = setInterval(() => {
      const token = localStorage.getItem("fb_access_token");
      if (token) {
        clearInterval(checkToken);
        localStorage.removeItem("fb_access_token");

        // const currentStepIndex = currentFlatStepIndex.value;
        // goToStep(currentStepIndex + 2);
      }
    }, 500);
  } else {
    // const currentStepIndex = currentFlatStepIndex.value;
    // goToStep(currentStepIndex + 2);
    goNext();
  }
}

window.addEventListener("message", (event) => {
  if (event.origin !== window.location.origin) return;
  if (event.data?.code) {
    console.log("Authorization code:", event.data.code);
  }
});

async function authWithGoogle(objective: CampaignObjective) {
  const adGroups: AdGroup[] = adStructure.ad_sets.map((adSet) => ({
    name: adSet.name,
    status: AdGroupStatus.PAUSED,
    ads: adSet.ads.map(() => ({
      headlines: [],
      descriptions: [],
      final_urls: [],
    })),
  }));

  googleAdsConnection.setAdGroups(adGroups);

  const data = await $api(
    `/v2/external/google-ads/status/${authStore.userEmail!}`,
  );

  googleAdsConnection.setCampaignObjective(objective);

  if (data.authenticated) {
    const currentStepIndex = currentFlatStepIndex.value;
    goToStep(currentStepIndex + 2);
    return;
  }

  googleAdsAuth.startLinking(authStore.userEmail!).then(() => {
    const checkLinked = setInterval(() => {
      if (googleAdsAuth.isLinked) {
        clearInterval(checkLinked);
        const currentStepIndex = currentFlatStepIndex.value;
        goToStep(currentStepIndex + 2);
      }
    }, 500);
  });
}
</script>

<template>
  <FormStepLayout>
    <h1 class="tw:mb-0 tw:text-4xl tw:font-bold">
      Choose Your Awareness Objective
    </h1>
    <p class="tw:text-secondary">
      Select the campaign type that aligns with your media strategy.
    </p>
    <hr class="tw:border-secondary/30" />
    <div
      v-if="adsConnection.connection === 'meta-ads'"
      class="tw:grid tw:gap-[18px] tw:lg:grid-cols-3"
    >
      <FunnelFlowHomeCard icon="ic:round-people-alt">
        <template #title>Reach</template>

        <template #description>
          Reach as many unique users as possible. Great for broad exposure.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="authWithFacebook('REACH')"
            >Select</Button
          >
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:chart-area-line">
        <template #title>Impressions</template>

        <template #description>
          Maximize ad views—even if users see it more than once.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="authWithFacebook('IMPRESSIONS')"
          >
            Select
          </Button>
        </template>
      </FunnelFlowHomeCard>
    </div>

    <div
      v-if="adsConnection.connection === 'google-ads'"
      class="tw:grid tw:gap-[18px] tw:lg:grid-cols-3"
    >
      <FunnelFlowHomeCard icon="tabler:users">
        <template #title>Website Traffic</template>

        <template #description>
          Drive more visitors to your website. Ideal for increasing site
          traffic.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="authWithGoogle(CampaignObjective.WEBSITE_TRAFFIC)"
            >Select</Button
          >
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:chart-area-line">
        <template #title>Product And Brand Consideration</template>

        <template #description>
          Encourage potential customers to explore your products and brand.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="
              authWithGoogle(CampaignObjective.PRODUCT_AND_BRAND_CONSIDERATION)
            "
          >
            Select
          </Button>
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:chart-area-line">
        <template #title>Brand Awareness</template>

        <template #description>
          Increase brand recognition among your target audience.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="authWithGoogle(CampaignObjective.BRAND_AWARENESS_AND_REACH)"
          >
            Select
          </Button>
        </template>
      </FunnelFlowHomeCard>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
