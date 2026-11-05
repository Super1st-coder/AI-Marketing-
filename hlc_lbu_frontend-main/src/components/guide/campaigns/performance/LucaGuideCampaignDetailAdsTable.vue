<script setup lang="ts">
import type { LucaGuideCampaignAdsTable } from "@/services/guide/LucaGuideCampaignsApi";
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import type { LucaGuideTimeframe } from "@/components/guide/LucaGuideTimeFilters.vue";
import { CLASSIFICATION_THRESHOLDS } from "@/constants/guide/classification-thresholds";

const props = defineProps<{
  campaignId: string;
  currency?: string;
}>();

const timeframe = ref<LucaGuideTimeframe>({ type: "max" });
const isLoading = ref(false);
const adsTable = ref<LucaGuideCampaignAdsTable>({
  kpis: [],
  ads: [],
  ad_sets: [],
  totals: { ad_count: 0, spend: 0, values: [] },
});

const { t } = useI18n();

async function loadAdsTable() {
  isLoading.value = true;

  try {
    const days =
      timeframe.value.type === "days"
        ? timeframe.value.days
        : timeframe.value.type === "max"
          ? LUCA_GUIDE_ENTIRE_PERIOD_DAYS
          : undefined;

    adsTable.value = await LucaGuideCampaignsApi.getAdsTable(
      props.campaignId,
      days,
    );
  } catch (error) {
    console.error("Failed to load ads table:", error);
    throw error;
  } finally {
    isLoading.value = false;
  }
}

watch(timeframe, loadAdsTable);

await loadAdsTable();

const stateFilter = ref<string | undefined>(undefined);

const stateOptions = computed(() =>
  CLASSIFICATION_THRESHOLDS.map((entry) => ({
    value: entry.key,
    label: t(
      `luca-guide.onboarding.classification-thresholds.statuses.${entry.key}`,
    ),
  })),
);

const filteredAds = computed(() => {
  if (!stateFilter.value) {
    return adsTable.value.ads;
  }

  return adsTable.value.ads.filter((ad) => ad.state === stateFilter.value);
});
</script>

<template>
  <div>
    <h2 class="tw:mb-2.5 tw:text-lg tw:font-bold">
      {{ $t("luca-guide.campaigns.detail.ads-table.title") }}
    </h2>

    <CardBase borderRadius="lg" class="tw:overflow-hidden">
      <LucaGuideCampaignDetailAdsDataTable
        :campaignId="campaignId"
        :ads="filteredAds"
        :kpis="adsTable.kpis"
        :currency="currency"
        :loading="isLoading"
      >
        <template #top>
          <div
            class="tw:flex tw:flex-col tw:items-center tw:justify-between tw:gap-2 tw:p-6 tw:lg:flex-row"
          >
            <div class="tw:lg:basis-52">
              <FieldBaseNewSelect
                v-model="stateFilter"
                name="ads-table-state-filter"
                :placeholder="
                  $t('luca-guide.campaigns.detail.ads-table.state-placeholder')
                "
                :options="stateOptions"
                hideLayout
                clearable
              />
            </div>

            <LucaGuideTimeFilters
              v-model="timeframe"
              :options="[7, 14, 30, 'max']"
              :disabled="isLoading"
            />
          </div>

          <Separator />
        </template>
      </LucaGuideCampaignDetailAdsDataTable>
    </CardBase>
  </div>
</template>
