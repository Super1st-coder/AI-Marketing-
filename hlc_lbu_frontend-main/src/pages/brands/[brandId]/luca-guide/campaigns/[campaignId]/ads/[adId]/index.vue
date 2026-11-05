<script setup lang="ts">
import LucaGuideAdsApi, {
  type LucaGuideAdDataDelivery,
  type LucaGuideAdDiagnosis,
  type LucaGuideAdInsightsStatus,
} from "@/services/guide/LucaGuideAdsApi";
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import LucaGuideOnboardingApi from "@/services/guide/LucaGuideOnboardingApi";
import {
  AdNotFoundError,
  CampaignNotFoundError,
} from "@/services/common-errors";

const store = useLucaGuideLayoutStore();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const campaignId = String(route.params.campaignId);
const adId = String(route.params.adId);

const [campaigns, ads, adAccounts] = await Promise.all([
  LucaGuideCampaignsApi.list(),
  LucaGuideAdsApi.list(),
  LucaGuideOnboardingApi.listMetaAdAccounts(),
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
      campaignId: campaignId,
    },
  });
}

const ad = ads.find(
  (item) =>
    item.ad_external_id === adId &&
    item.campaign_external_id === campaign.external_id,
);

if (!ad) {
  throw new AdNotFoundError();
}

const adExternalId = ad.ad_external_id;

const adAccountName = computed(() => {
  const selectedAccountId = store.meta?.selected_ad_account_id;
  const matchedAccount = adAccounts.find(
    (account) => account.id === selectedAccountId,
  );

  return matchedAccount?.name ?? store.brand?.name ?? "—";
});

usePageTitle(() =>
  t("routes.luca-guide-campaign-ad", {
    brand: store.brand?.name ?? "",
    campaign: campaign.name,
    ad: ad.ad_name ?? ad.ad_external_id,
  }),
);

// HLG-158: keep the page badge in sync with the Performance Summary's windowed
// classification (they were disagreeing — badge lifetime, text windowed). Starts
// on the ad's stored state until the summary reports the selected window's state.
const windowedState = ref(ad.state);

const isGenerating = ref(false);
const generationError = ref<string | null>(null);
const isLoadingDataDelivery = ref(false);
// The date window currently selected in the performance summary — passed to the diagnosis so it
// reflects the chosen dates (Marco).
const selectedWindow = ref<{ startDate?: string; endDate?: string }>();
const diagnosis = ref<LucaGuideAdDiagnosis | null>(null);
const insightsStatus = ref<LucaGuideAdInsightsStatus | null>(null);
const dataDelivery = ref<LucaGuideAdDataDelivery | null>(null);

// HLG-181: restore the latest saved diagnosis (and its insights status) when the page opens, so a
// generated diagnosis persists across reloads instead of showing "Generate" again — the All-Ads
// "Diag: Yes" column and the detail page must agree, and the user shouldn't re-spend a generation
// every visit. null → none yet → the empty-state "Generate" card shows; Re-generate still replaces
// it explicitly. Non-fatal: a failed read just falls back to the empty state (same as today).
diagnosis.value = await LucaGuideAdsApi.getDiagnosis(adExternalId);
if (diagnosis.value) {
  insightsStatus.value = await LucaGuideAdsApi.getInsightsStatus(
    adExternalId,
  ).catch(() => null);
}

const completedSlotIndexes = computed(() =>
  (insightsStatus.value?.slots ?? [])
    .filter((slot) => slot.status === "completed")
    .map((slot) => slot.slot_index),
);

async function loadDataDelivery() {
  isLoadingDataDelivery.value = true;

  try {
    dataDelivery.value = await LucaGuideAdsApi.getDataDelivery(adExternalId);
  } catch (error) {
    console.error("Failed to load data-delivery recommendations:", error);
    throw error;
  } finally {
    isLoadingDataDelivery.value = false;
  }
}

async function generateDiagnosis() {
  isGenerating.value = true;
  generationError.value = null;
  insightsStatus.value = null;
  dataDelivery.value = null;

  try {
    // Generate diagnosis slots for the currently-selected date window (Marco: analysis must reflect
    // the dates; a fresh regenerate on a new window produces a new analysis).
    diagnosis.value = await LucaGuideAdsApi.generateDiagnosis(
      adExternalId,
      selectedWindow.value,
    );

    // Start insights generation
    await LucaGuideAdsApi.startInsights(adExternalId);

    // Poll insights status
    await pooling(
      async () => {
        const status = await LucaGuideAdsApi.getInsightsStatus(adExternalId);
        insightsStatus.value = status;
        return status;
      },
      (status) => status.all_completed,
      5 * SECOND_IN_MS,
      { timeoutMs: 10 * MINUTE_IN_MS },
    );

    await loadDataDelivery();
  } catch (error) {
    // HLG-178: surface the failure instead of failing silently. If nothing was
    // generated, drop back to the empty state so the Alert + retry button show.
    console.error("Failed to generate diagnosis:", error);
    generationError.value = t("luca-guide.ads.detail.diagnosis.generate-error");
    if (!diagnosis.value) {
      insightsStatus.value = null;
    }
  } finally {
    isGenerating.value = false;
  }
}

const breadcrumbs = computed(() => [
  {
    label: t("luca-guide.campaigns.label"),
    to: { name: "LucaGuideCampaigns" },
  },
  {
    label: t("luca-guide.campaigns.detail.performance-label"),
    to: {
      name: "LucaGuideCampaign",
      params: { campaignId: campaignId },
    },
  },
  {
    label: t("luca-guide.ads.detail.breadcrumb"),
  },
]);
</script>

<template>
  <div class="tw:flex tw:h-full tw:flex-col">
    <div class="tw:border-b tw:border-divider tw:px-7 tw:py-2">
      <Breadcrumbs :data="breadcrumbs" />
    </div>

    <ContainerDashboard :maxWidth="1196">
      <PageTitle>
        {{ ad.ad_name || "—" }}

        <template v-if="ad.headline" #description>
          {{ ad.headline }}
        </template>

        <template #after>
          <LucaGuideAdClassificationChip :state="windowedState ?? ad.state" />
        </template>
      </PageTitle>

      <div
        class="tw:grid tw:grid-cols-1 tw:items-start tw:gap-5 tw:xl:grid-cols-[1fr_337px]"
      >
        <LucaGuideAdPreviewPanel
          :ad="ad"
          :accountName="adAccountName"
          class="tw:xl:order-last"
        />

        <div class="tw:flex tw:flex-col tw:gap-5">
          <LucaGuideAdPerformanceSummary
            :adExternalId="ad.ad_external_id"
            :currency="store.currency"
            @window-change="(w) => (selectedWindow = w)"
            @update:windowed-state="windowedState = $event ?? ad.state"
          />

          <!-- HLG-178: surface a diagnosis-generation failure instead of failing
               silently; retry via the empty-state / Re-generate button below. -->
          <Alert v-if="generationError" type="error">
            {{ generationError }}
          </Alert>

          <CardBase v-if="!diagnosis && !isGenerating">
            <LucaGuideEmptyState
              icon="tabler:microscope"
              :maxWidth="450"
              :title="$t('luca-guide.ads.detail.diagnosis.title')"
              :description="$t('luca-guide.ads.detail.diagnosis.description')"
            >
              <Button
                type="button"
                size="md"
                leftIcon="tabler:chart-bar"
                :isLoading="isGenerating"
                @click="generateDiagnosis"
              >
                {{ $t("luca-guide.ads.detail.diagnosis.button") }}
              </Button>
            </LucaGuideEmptyState>
          </CardBase>

          <template v-else>
            <LucaGuideAdDiagnosis
              :ad="ad"
              :campaign="campaign"
              :accountName="adAccountName"
              :isLoading="isGenerating && !diagnosis"
              :isGenerating="isGenerating"
              :completedSlotIndexes="completedSlotIndexes"
              :assetType="diagnosis?.asset_type ?? ad.asset_type"
              :cards="diagnosis?.cards"
              :window="selectedWindow"
              @re-generate="generateDiagnosis"
            />

            <LucaGuideAdRecommendedNextMove
              :ad="ad"
              :campaign="campaign"
              :accountName="adAccountName"
              :isLoading="isGenerating || isLoadingDataDelivery"
              :dataDelivery="dataDelivery"
              @re-generate="loadDataDelivery"
            />
          </template>
        </div>
      </div>
    </ContainerDashboard>
  </div>
</template>
