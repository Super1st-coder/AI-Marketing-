<script setup lang="ts">
import { CampaignData } from "@/services/projects/CampaignsApi";
import { useFunnelPaidSocialLaunchpadPreCheckStore } from "@/stores/funnel-flow/paid-social/FunnelPaidSocialLaunchpadPreCheckStore.ts";

defineProps<{
  campaign: CampaignData;
}>();

const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

const { t } = useI18n();

const adSetsCount = computed(() => {
  const adSetIds = new Set(
    preCheckStore.creativesWithData.map((creative) => creative.adset_id),
  );

  return adSetIds.size;
});

const campaignObjective = computed(() => {
  const objective =
    preCheckStore.preCheckResponse?.data.campaign.objective ?? "";
  return objective
    ? t(`meta-ads.objectives.${objective}.title`, objective)
    : objective;
});

const optimizationGoal = computed(() => {
  const objective = preCheckStore.preCheckResponse?.data.campaign.objective;
  const goal =
    preCheckStore.preCheckResponse?.data.campaign.optimization_goal ?? "";
  return goal
    ? t(
        `meta-ads.objectives.${objective}.optimization-goals.${goal}.title`,
        goal,
      )
    : goal;
});

// Only set for Leads optimized for conversions on the website
const conversionEvent = computed(() => {
  const event = preCheckStore.launchConfiguration?.conversion_event;
  return event ? t(`meta-ads.conversion-events.${event}.title`, event) : "";
});

const campaignMode = computed(() => {
  const mode = preCheckStore.preCheckResponse?.data.campaign.mode ?? "";
  return mode ? t(`meta-ads.campaign-modes.${mode}.title`, mode) : mode;
});
</script>

<template>
  <AdsLaunchpadCampaignHeaderStatsList>
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
        <template #value> {{ adSetsCount }} </template>
      </AdsLaunchpadCampaignHeaderStatsListItem>
    </AdsLaunchpadCampaignHeaderStatsList>

    <AdsLaunchpadCampaignHeaderStatsList>
      <AdsLaunchpadCampaignHeaderStatsListItem>
        <template #label>
          {{
            $t("funnel-flow.paid-social.launchpad.common.campaign-objective")
          }}
        </template>
        <template #value> {{ campaignObjective }} </template>
      </AdsLaunchpadCampaignHeaderStatsListItem>

      <AdsLaunchpadCampaignHeaderStatsListItem>
        <template #label>
          {{ $t("funnel-flow.paid-social.launchpad.common.optimization-goal") }}
        </template>
        <template #value> {{ optimizationGoal }} </template>
      </AdsLaunchpadCampaignHeaderStatsListItem>

      <AdsLaunchpadCampaignHeaderStatsListItem v-if="conversionEvent">
        <template #label>
          {{ $t("funnel-flow.paid-social.launchpad.common.conversion-event") }}
        </template>
        <template #value> {{ conversionEvent }} </template>
      </AdsLaunchpadCampaignHeaderStatsListItem>

      <AdsLaunchpadCampaignHeaderStatsListItem>
        <template #label>
          {{ $t("funnel-flow.paid-social.launchpad.common.campaign-mode") }}
        </template>
        <template #value> {{ campaignMode }} </template>
      </AdsLaunchpadCampaignHeaderStatsListItem>

      <AdsLaunchpadCampaignHeaderStatsListItem>
        <template #label>
          {{
            $t("funnel-flow.paid-social.launchpad.common.budget-optimization")
          }}
        </template>
        <template #value>
          {{ $t("funnel-flow.paid-social.launchpad.common.cbo") }}
        </template>
      </AdsLaunchpadCampaignHeaderStatsListItem></AdsLaunchpadCampaignHeaderStatsList
    >
  </AdsLaunchpadCampaignHeaderStatsList>
</template>
