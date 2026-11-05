<script setup lang="ts">
import ChannelConnections, {
  MetaInsightsResponse,
  type MetaCampaignInsight,
  type MetaInsightAction,
} from "@/services/funnel-flow/ChannelConnections";

const { t, locale } = useI18n();

const store = useBrandLayoutStore();
usePageTitle(() => t("routes.insights", { brand: store.brand?.name ?? "" }));

const isAuthenticated = ref(false);
const selectedAdAccountId = ref<string | undefined>();
const campaignInsights = ref<MetaCampaignInsight[]>([]);
const isLoadingCampaignInsights = ref(false);
const isLoadingMoreInsights = ref(false);
const hasNextPage = ref(false);
const nextPageUrl = ref<string | undefined>();
const search = ref("");

const INSIGHTS_FIELDS =
  "campaign_id,campaign_name,impressions,reach,spend,clicks,conversions,ctr,cpc,date_start,date_stop,account_currency";

type InsightsDatePreset = "last_7d" | "last_14d" | "last_30d";

const selectedDatePreset = ref<InsightsDatePreset>("last_7d");

const datePresetOptions: { value: InsightsDatePreset; days: number }[] = [
  { value: "last_7d", days: 7 },
  { value: "last_14d", days: 14 },
  { value: "last_30d", days: 30 },
];

const selectedAccountCurrency = ref<string | undefined>();

const tableHeaders = computed(() => [
  {
    title: t("brands.insights.columns.campaign"),
    key: "campaign_name",
    sortable: false,
  },
  {
    title: t("brands.insights.columns.impressions"),
    key: "impressions",
    sortable: false,
  },
  {
    title: t("brands.insights.columns.reach"),
    key: "reach",
    sortable: false,
  },
  {
    title: selectedAccountCurrency.value
      ? t("brands.insights.columns.spend-with-currency", {
          currency: selectedAccountCurrency.value,
        })
      : t("brands.insights.columns.spend"),
    key: "spend",
    sortable: false,
  },
  {
    title: t("brands.insights.columns.clicks"),
    key: "clicks",
    sortable: false,
  },
  {
    title: t("brands.insights.columns.conversions"),
    key: "conversions",
    sortable: false,
  },
  {
    title: t("brands.insights.columns.ctr"),
    key: "ctr",
    sortable: false,
  },
  {
    title: selectedAccountCurrency.value
      ? t("brands.insights.columns.cpc-with-currency", {
          currency: selectedAccountCurrency.value,
        })
      : t("brands.insights.columns.cpc"),
    key: "cpc",
    sortable: false,
  },
  {
    title: t("brands.insights.columns.period"),
    key: "period",
    sortable: false,
  },
]);

function updatePaginationState(response: MetaInsightsResponse) {
  nextPageUrl.value = response.paging?.next;
  hasNextPage.value = Boolean(nextPageUrl.value);
}

function resetInsightsPagination() {
  campaignInsights.value = [];
  hasNextPage.value = false;
  nextPageUrl.value = undefined;
  selectedAccountCurrency.value = undefined;
}

function syncAccountCurrencyFromInsights(insights: MetaCampaignInsight[]) {
  const currency = insights.find(
    (row) => row.account_currency,
  )?.account_currency;

  if (currency) {
    selectedAccountCurrency.value = currency;
  }
}

async function fetchInitialCampaignInsights(accountId: string) {
  isLoadingCampaignInsights.value = true;
  resetInsightsPagination();

  try {
    const response = await ChannelConnections.getInsights(accountId, {
      level: "campaign",
      fields: INSIGHTS_FIELDS,
      date_preset: selectedDatePreset.value,
    });
    campaignInsights.value = response.data;
    syncAccountCurrencyFromInsights(response.data);
    updatePaginationState(response);
  } catch (error) {
    console.error("Failed to fetch campaign insights:", error);
    resetInsightsPagination();
  } finally {
    isLoadingCampaignInsights.value = false;
  }
}

async function loadMoreCampaignInsights() {
  if (!nextPageUrl.value || isLoadingMoreInsights.value) {
    return;
  }

  isLoadingMoreInsights.value = true;

  try {
    const response = await ChannelConnections.getInsightsByNextUrl(
      nextPageUrl.value,
    );
    campaignInsights.value.push(...response.data);
    updatePaginationState(response);
  } catch (error) {
    console.error("Failed to load more campaign insights:", error);
  } finally {
    isLoadingMoreInsights.value = false;
  }
}

watch(selectedAdAccountId, async (accountId) => {
  if (!accountId) {
    resetInsightsPagination();
    return;
  }

  await fetchInitialCampaignInsights(accountId);
});

watch(selectedDatePreset, async () => {
  if (!selectedAdAccountId.value) {
    return;
  }

  await fetchInitialCampaignInsights(selectedAdAccountId.value);
});

function formatNumber(value?: string) {
  if (!value) {
    return "—";
  }

  const castedValue = castStringToNumber(value);
  return formatNumberValue(castedValue, DEFAULT_NUMBER_LOCALE);
}

function formatConversions(conversions?: MetaInsightAction[]) {
  if (!conversions?.length) {
    return "—";
  }

  const total = conversions.reduce(
    (sum, item) => sum + (castStringToNumber(item.value) || 0),
    0,
  );

  return formatNumberValue(total, DEFAULT_NUMBER_LOCALE);
}

function formatCurrency(value?: string) {
  if (!value) {
    return "—";
  }

  const amount = castStringToNumber(value);

  return formatCurrencyValue(
    amount,
    DEFAULT_NUMBER_LOCALE,
    selectedAccountCurrency.value,
  );
}

function formatPercent(value?: string) {
  if (!value) {
    return "—";
  }

  const castedValue = castStringToNumber(value);
  return formatPercentValue(castedValue, DEFAULT_NUMBER_LOCALE);
}

function formatPeriod(dateStart?: string, dateStop?: string) {
  if (!dateStart || !dateStop) {
    return "—";
  }

  return formatDateRange(
    parseIsoDate(dateStart),
    parseIsoDate(dateStop),
    locale.value,
  );
}

function handleDisconnect() {
  resetInsightsPagination();
}
</script>

<template>
  <PageTitle>
    {{ $t("global.insights") }}
  </PageTitle>

  <AdChannelDestinationCard
    v-model:ad-account-id="selectedAdAccountId"
    v-model:authenticated="isAuthenticated"
    :show-page-select="false"
    @disconnect="handleDisconnect"
  />

  <CardBase
    v-if="isAuthenticated"
    class="tw:mt-6"
    :disabled="
      !selectedAdAccountId || isLoadingCampaignInsights || isLoadingMoreInsights
    "
  >
    <VDataTable
      v-model:search="search"
      :items="campaignInsights"
      :headers="tableHeaders"
      :loading="isLoadingCampaignInsights || isLoadingMoreInsights"
      :loading-text="$t('brands.insights.loading-campaigns')"
      :items-per-page="-1"
      itemValue="campaign_id"
      hideDefaultFooter
    >
      <template #top>
        <div
          class="tw:flex tw:flex-col tw:gap-4 tw:px-8 tw:py-5 tw:lg:flex-row tw:lg:items-center tw:lg:justify-between"
        >
          <div class="tw:flex tw:flex-wrap tw:gap-2">
            <Button
              v-for="option in datePresetOptions"
              :key="option.value"
              type="button"
              size="sm"
              :variant="
                selectedDatePreset === option.value ? 'solid' : 'outlined'
              "
              :color="
                selectedDatePreset === option.value ? 'primary' : 'secondary'
              "
              @click="selectedDatePreset = option.value"
            >
              {{ $t("brands.insights.last-days", { days: option.days }) }}
            </Button>
          </div>
        </div>

        <Separator />
      </template>

      <template #no-data>
        <p class="tw:py-8 tw:text-center tw:text-gray-500">
          {{
            selectedAdAccountId
              ? $t("global.no-data-available")
              : $t("brands.insights.select-account-hint")
          }}
        </p>
      </template>

      <template #item.campaign_name="{ item }">
        <div>
          <div class="tw:font-semibold">
            {{ item.campaign_name ?? item.campaign_id }}
          </div>

          <div
            v-if="item.campaign_name && item.campaign_id"
            class="tw:text-sm tw:text-secondary-text"
          >
            {{ item.campaign_id }}
          </div>
        </div>
      </template>

      <template #item.impressions="{ item }">
        {{ formatNumber(item.impressions) }}
      </template>

      <template #item.reach="{ item }">
        {{ formatNumber(item.reach) }}
      </template>

      <template #item.spend="{ item }">
        {{ formatCurrency(item.spend) }}
      </template>

      <template #item.clicks="{ item }">
        {{ formatNumber(item.clicks) }}
      </template>

      <template #item.conversions="{ item }">
        {{ formatConversions(item.conversions) }}
      </template>

      <template #item.ctr="{ item }">
        {{ formatPercent(item.ctr) }}
      </template>

      <template #item.cpc="{ item }">
        {{ formatCurrency(item.cpc) }}
      </template>

      <template #item.period="{ item }">
        {{ formatPeriod(item.date_start, item.date_stop) }}
      </template>

      <template #bottom>
        <div v-if="selectedAdAccountId && campaignInsights.length">
          <Separator />

          <div
            class="tw:flex tw:flex-col tw:items-center tw:justify-between tw:gap-4 tw:px-8 tw:py-5 tw:md:flex-row"
          >
            <p class="tw:grow tw:basis-0 tw:text-secondary-text">
              {{
                $t("brands.insights.loaded-campaigns", {
                  count: campaignInsights.length,
                })
              }}
            </p>

            <div class="tw:flex tw:grow tw:basis-0 tw:justify-center">
              <Button
                v-if="hasNextPage"
                type="button"
                color="primary"
                size="sm"
                :isLoading="isLoadingMoreInsights"
                :disabled="isLoadingCampaignInsights"
                @click="loadMoreCampaignInsights"
              >
                {{ $t("brands.insights.load-more") }}
              </Button>
            </div>

            <div class="tw:grow tw:basis-0"></div>
          </div>
        </div>
      </template>
    </VDataTable>
  </CardBase>
</template>
