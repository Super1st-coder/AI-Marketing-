<script setup lang="ts">
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import { CampaignNotFoundError } from "@/services/common-errors";
import { LUCA_GUIDE_ENTIRE_PERIOD_DAYS } from "@/constants/guide/timeframe";

const store = useLucaGuideLayoutStore();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const campaignId = String(route.params.campaignId);

// HLG-193: the header stats (spend/impressions/conversions/ad count) read from the ads-table
// "Entire period" totals — which the backend now windows over the loaded daily span — so the header
// matches the ad-set list + ads table below it (and Ads Manager) instead of the stored all-time
// /ads aggregate, which over-counted ads older than the ingested window.
const [campaigns, kpis, kpiOptions, adsTable] = await Promise.all([
  LucaGuideCampaignsApi.list(),
  LucaGuideCampaignsApi.getKpis(campaignId),
  LucaGuideCampaignsApi.getKpiOptions(campaignId),
  LucaGuideCampaignsApi.getAdsTable(campaignId, LUCA_GUIDE_ENTIRE_PERIOD_DAYS),
]);

const campaign = campaigns.find((item) => item.campaign_id === campaignId);

if (!campaign) {
  throw new CampaignNotFoundError();
}

if (!campaign.has_primary_kpi) {
  await router.replace({
    name: "LucaGuideCampaignOnboarding",
    params: {
      brandId: route.params.brandId,
      campaignId,
    },
  });
}

// Windowed totals (loaded daily span) for the header; fall back to 0 on older backends that don't
// yet return impressions/conversions in the ads-table totals.
const spend = adsTable.totals.spend;
const impressions = adsTable.totals.impressions ?? 0;
const conversions = adsTable.totals.conversions ?? 0;
const adCount = adsTable.totals.ad_count;

usePageTitle(() =>
  t("routes.luca-guide-campaign", {
    brand: store.brand?.name ?? "",
    campaign: campaign.name,
  }),
);

function goToBrief() {
  router.push({
    name: "LucaGuideCampaignBrief",
    params: {
      brandId: route.params.brandId,
      campaignId,
    },
  });
}

const breadcrumbs = computed(() => [
  {
    label: t("luca-guide.campaigns.label"),
    to: { name: "LucaGuideCampaigns" },
  },
  {
    label: t("luca-guide.campaigns.detail.performance-label"),
  },
]);
</script>

<template>
  <div class="tw:flex tw:h-full tw:flex-col">
    <div class="tw:border-b tw:border-divider tw:px-7 tw:py-2">
      <Breadcrumbs :data="breadcrumbs" />
    </div>

    <ContainerDashboard :maxWidth="1096">
      <PageTitle>
        {{ campaign.name }}
        <span
          class="tw:ml-1 tw:text-sm tw:font-normal tw:text-gray-400 tw:lg:text-base"
        >
          · {{ $t("luca-guide.campaigns.detail.performance-label") }}
        </span>

        <template #description>
          {{ $t("luca-guide.campaigns.detail.description") }}
        </template>

        <template #actions>
          <!-- TODO: restore View History button -->

          <!-- <Button
            :to="{
              name: 'LucaGuideCampaignHistory',
              params: { brandId: route.params.brandId, campaignId },
            }"
            variant="outlined"
            color="secondary"
            size="sm"
            leftIcon="tabler:history"
          >
            {{ $t("luca-guide.campaigns.detail.view-history") }}
          </Button> -->

          <Button
            :to="{
              name: 'LucaGuideCampaignBrief',
              params: { brandId: route.params.brandId, campaignId },
            }"
            variant="label"
            color="primary"
            size="sm"
            leftIcon="tabler:file-text"
          >
            {{ $t("luca-guide.campaigns.detail.view-brief") }}
          </Button>
        </template>
      </PageTitle>

      <LucaGuideCampaignDetailNorthStar
        class="tw:mt-6"
        :kpis="kpis"
        :kpiOptions="kpiOptions"
        :spend="spend"
        :impressions="impressions"
        :conversions="conversions"
        :adCount="adCount"
        :currency="store.currency"
        @editMetrics="goToBrief"
      />

      <LucaGuideCampaignDetailAnalysis
        :campaignId="campaignId"
        :currency="store.currency"
      />

      <LucaGuideCampaignDetailAdSets
        :campaignId="campaignId"
        :currency="store.currency"
      />

      <LucaGuideCampaignDetailAdsTable
        :campaignId="campaignId"
        :currency="store.currency"
      />
    </ContainerDashboard>
  </div>
</template>
