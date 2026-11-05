<script setup lang="ts">
import type { LucaGuideOverviewCampaign } from "@/services/guide/LucaGuideCampaignsApi";

const props = defineProps<{
  campaigns: LucaGuideOverviewCampaign[];
  currency: string;
}>();

const { t, te, locale } = useI18n();

const activeCampaigns = computed(() =>
  props.campaigns.filter((campaign) => campaign.has_primary_kpi),
);
const pendingCampaigns = computed(() =>
  props.campaigns.filter((campaign) => !campaign.has_primary_kpi),
);

const currentTab = ref("active");

const headerNowrapProps = { class: "tw:whitespace-nowrap" };

const sortBy = ref<{ key: string; order: "asc" | "desc" }[]>([]);

function comparePrimaryNorthStar(
  a: LucaGuideOverviewCampaign,
  b: LucaGuideOverviewCampaign,
) {
  return compareNullableNumbers(
    a.primary?.value,
    b.primary?.value,
    sortBy.value.some(
      (item) => item.key === "primary_north_star" && item.order === "desc",
    ),
  );
}

const activeTableHeaders = computed(() => [
  {
    title: t("luca-guide.campaigns.list.columns.status"),
    key: "status",
    sortable: true,
    headerProps: headerNowrapProps,
  },
  {
    title: t("luca-guide.campaigns.list.columns.campaign-name"),
    key: "name",
    sortable: true,
    headerProps: headerNowrapProps,
  },
  {
    title: t("luca-guide.campaigns.list.columns.primary-north-star"),
    key: "primary_north_star",
    sortable: true,
    sortRaw: comparePrimaryNorthStar,
    headerProps: headerNowrapProps,
  },
  {
    title: t("luca-guide.campaigns.list.columns.spend"),
    key: "spend",
    sortable: true,
    headerProps: headerNowrapProps,
  },
  {
    title: t("luca-guide.campaigns.list.columns.actions"),
    key: "actions",
    sortable: false,
    align: "end" as const,
    headerProps: headerNowrapProps,
    nowrap: true,
  },
]);

const pendingTableHeaders = computed(() => [
  {
    title: t("luca-guide.campaigns.list.columns.campaign-name"),
    key: "name",
    sortable: true,
    headerProps: headerNowrapProps,
  },
  {
    title: t("luca-guide.campaigns.list.columns.actions"),
    key: "actions",
    sortable: false,
    align: "end" as const,
    headerProps: headerNowrapProps,
    nowrap: true,
  },
]);

function formatSpend(value: number) {
  return formatCurrencyValue(value, locale.value, props.currency);
}

function kpiLabel(key: string, name: string) {
  const shortKey = `luca-guide.kpis.${key}.short`;
  return te(shortKey) ? t(shortKey) : name;
}

function kpiValueClass(good: boolean | null, lowerBetter: boolean) {
  if (good === true) {
    return "tw:text-success";
  }

  if (good === false) {
    return lowerBetter ? "tw:text-error" : "tw:text-warning";
  }

  return "tw:text-gray-900";
}
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-4">
    <Tabs v-model="currentTab" size="sm">
      <template #list>
        <Tab value="active" icon="tabler:chart-dots">
          {{ $t("luca-guide.campaigns.list.tabs.active") }}
        </Tab>

        <Tab value="pending" icon="tabler:hourglass">
          {{
            $t("luca-guide.campaigns.list.tabs.pending", {
              count: pendingCampaigns.length,
            })
          }}
        </Tab>
      </template>

      <TabPanel value="active" class="tw:pt-4">
        <CardBase v-if="activeCampaigns.length" class="tw:overflow-hidden">
          <VDataTable
            :items="activeCampaigns"
            :headers="activeTableHeaders"
            v-model:sort-by="sortBy"
            :items-per-page="-1"
            item-value="campaign_id"
            hide-default-footer
          >
            <template #item.status="{ item }">
              <LucaGuideCampaignStatusChip :status="item.status" />
            </template>

            <template #item.name="{ item }">
              <LucaGuideCampaignIdentity
                class="tw:py-2"
                :name="item.name"
                :objective="item.objective"
                :hasContext="item.context_status === 'with'"
              />
            </template>

            <template #item.primary_north_star="{ item }">
              <div
                v-if="item.primary"
                class="tw:flex tw:flex-col tw:gap-0.5 tw:py-1"
              >
                <span
                  class="tw:text-xs tw:font-medium tw:text-secondary-text tw:uppercase"
                >
                  {{ kpiLabel(item.primary.key, item.primary.name) }}
                </span>

                <p class="tw:leading-tight">
                  <span
                    class="tw:text-sm tw:font-bold"
                    :class="
                      kpiValueClass(
                        item.primary.good,
                        item.primary.lower_better,
                      )
                    "
                  >
                    {{
                      formatLucaGuideKpiValue(
                        item.primary.value,
                        item.primary.format,
                        locale,
                        currency,
                      )
                    }}
                  </span>

                  <span class="tw:text-xs tw:text-secondary-text">
                    /
                    {{
                      formatLucaGuideKpiValue(
                        item.primary.target,
                        item.primary.format,
                        locale,
                        currency,
                      )
                    }}
                  </span>
                </p>
              </div>

              <span v-else class="tw:text-secondary-text">—</span>
            </template>

            <template #item.spend="{ item }">
              {{ formatSpend(item.spend) }}
            </template>

            <template #item.actions="{ item }">
              <Link
                :to="{
                  name: 'LucaGuideCampaign',
                  params: { campaignId: item.campaign_id },
                }"
                icon="tabler:chevron-right"
                class="tw:text-sm tw:font-medium"
              >
                {{ $t("luca-guide.home.campaigns.view-campaign") }}
              </Link>
            </template>
          </VDataTable>
        </CardBase>

        <LucaGuideEmptyState
          v-else
          class="tw:min-h-[303px]"
          :title="$t('luca-guide.campaigns.list.empty.active.title')"
          :description="
            $t('luca-guide.campaigns.list.empty.active.description')
          "
        >
          <Button type="button" size="md" @click="currentTab = 'pending'">
            {{
              $t("luca-guide.campaigns.list.empty.active.button", {
                count: pendingCampaigns.length,
              })
            }}
          </Button>
        </LucaGuideEmptyState>
      </TabPanel>

      <TabPanel value="pending" class="tw:pt-4">
        <div
          v-if="pendingCampaigns.length"
          class="tw:flex tw:flex-col tw:gap-4"
        >
          <Alert type="warning">
            <template #title>
              {{
                $t("luca-guide.campaigns.list.alert.title", {
                  count: pendingCampaigns.length,
                })
              }}
            </template>

            {{ $t("luca-guide.campaigns.list.alert.description") }}
          </Alert>

          <CardBase class="tw:overflow-hidden">
            <VDataTable
              :items="pendingCampaigns"
              :headers="pendingTableHeaders"
              :items-per-page="-1"
              item-value="campaign_id"
              hide-default-footer
            >
              <template #item.name="{ item }">
                <LucaGuideCampaignIdentity
                  class="tw:py-2"
                  :name="item.name"
                  :objective="item.objective"
                  :hasContext="item.context_status === 'with'"
                />
              </template>

              <template #item.actions="{ item }">
                <Link
                  :to="{
                    name: 'LucaGuideCampaign',
                    params: { campaignId: item.campaign_id },
                  }"
                  icon="tabler:chevron-right"
                  class="tw:text-sm tw:font-medium"
                >
                  {{ $t("luca-guide.home.campaigns.start-analysis-setup") }}
                </Link>
              </template>
            </VDataTable>
          </CardBase>
        </div>

        <LucaGuideEmptyState
          v-else
          class="tw:min-h-[303px]"
          :title="$t('luca-guide.campaigns.list.empty.pending.title')"
          :description="
            $t('luca-guide.campaigns.list.empty.pending.description')
          "
        />
      </TabPanel>
    </Tabs>
  </div>
</template>
