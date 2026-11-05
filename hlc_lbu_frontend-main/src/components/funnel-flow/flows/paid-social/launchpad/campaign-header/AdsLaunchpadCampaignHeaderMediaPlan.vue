<script setup lang="ts">
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import { CampaignData } from "@/services/projects/CampaignsApi";
import { FunnelPaidSocialFormData } from "../../FunnelPaidSocialForm.vue";
import AdsApi, {
  getChannelSelectedVariant,
} from "@/services/funnel-flow/paid-social/AdsApi";

defineProps<{
  campaign: CampaignData;
}>();

const { data } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const brandId = useBrandId();
const campaignId = useCampaignId();

// Fetch ad structure
const { data: adStructure } = await AdStructureApi.getAdStructureByChannelGroup(
  brandId,
  campaignId,
  data.value.channelGroupId,
);

// Fetch the ads
const ads = await Promise.all(
  adStructure.ad_sets.map(
    async (set) =>
      await Promise.all(
        set.ads.map(
          async (ad) =>
            (await AdsApi.getOneAd(brandId, campaignId, ad.id)).data,
        ),
      ),
  ),
);

const adsAmount = computed(() => {
  let total = 0;
  adStructure.ad_sets.forEach((adSet) => {
    total += adSet.ads.length;
  });

  return total;
});

const formatsAmount = computed(() => {
  const formatsByAdset = adStructure.ad_sets.map((_, index) => {
    const adsSets = ads[index];

    let formatCount = 0;

    adsSets.forEach((ad) => {
      ad.ad_channels.forEach((channel) => {
        const selectedVariant = getChannelSelectedVariant(channel);
        if (selectedVariant?.media.formats) {
          formatCount += selectedVariant.media.formats.length;
        }
      });
    });

    return formatCount;
  });

  return formatsByAdset.reduce((sum, set) => sum + set, 0);
});
</script>

<template>
  <AdsLaunchpadCampaignHeaderStatsList>
    <AdsLaunchpadCampaignHeaderStatsListItem>
      <template #label>
        {{ $t("funnel-flow.paid-social.launchpad.common.selected-channel") }}
      </template>
      <template #value>
        {{ $t("funnel-flow.paid-social.launchpad.common.meta") }}
      </template>
    </AdsLaunchpadCampaignHeaderStatsListItem>

    <AdsLaunchpadCampaignHeaderStatsListItem>
      <template #label>
        {{ $t("funnel-flow.paid-social.launchpad.common.ad-sets") }}
      </template>
      <template #value> {{ adStructure.ad_sets.length }} </template>
    </AdsLaunchpadCampaignHeaderStatsListItem>

    <AdsLaunchpadCampaignHeaderStatsListItem>
      <template #label>
        {{ $t("funnel-flow.paid-social.summary.sets.ads.title") }}
      </template>
      <template #value> {{ adsAmount }} </template>
    </AdsLaunchpadCampaignHeaderStatsListItem>

    <AdsLaunchpadCampaignHeaderStatsListItem>
      <template #label>
        {{ $t("funnel-flow.paid-social.summary.sets.ads.media-formats-label") }}
      </template>
      <template #value> {{ formatsAmount }} </template>
    </AdsLaunchpadCampaignHeaderStatsListItem>
  </AdsLaunchpadCampaignHeaderStatsList>
</template>
