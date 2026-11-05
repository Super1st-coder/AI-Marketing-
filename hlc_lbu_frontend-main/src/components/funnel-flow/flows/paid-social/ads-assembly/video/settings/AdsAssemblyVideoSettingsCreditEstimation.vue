<script setup lang="ts">
import { DataTableHeader } from "vuetify";

export interface AdsAssemblyVideoSettingsEstimationBreakdownItem {
  operation: string;
  quantity: number;
  unitCost: number;
  subtotal: number;
}

export interface AdsAssemblyVideoSettingsEstimation {
  /** `undefined` while the estimate is loading or couldn't be computed. */
  totalCost?: number;
  /** Ads in the ad set: the total covers all of them, while Continue generates one at a time. */
  adsCount?: number;
  /** Shown under the breakdown, e.g. when some step couldn't be priced and the total is a minimum. */
  note?: string;
  /** Shown as a warning, e.g. when the whole batch costs more than the available balance. */
  warning?: string;
  /** `undefined` while the balance is unknown (not loaded, or the credits service is down). */
  availableBalance?: number;
  breakdown: AdsAssemblyVideoSettingsEstimationBreakdownItem[];
}

const props = defineProps<{
  estimation: AdsAssemblyVideoSettingsEstimation;
}>();

const { t, locale } = useI18n();

/** Whole Lucas, rounded up: the screen never shows less than what may be charged. */
function formatLucas(value: number | undefined) {
  return value === undefined
    ? "—"
    : formatNumberValue(Math.ceil(value), locale.value);
}

/** "3 ads": says outright that the total is the whole ad set, not the Continue button's step. */
const adsLabel = computed(() => {
  const count = props.estimation.adsCount ?? 0;
  return t(
    "funnel-flow.paid-social.ads.video.settings.credit-estimation.ads-count",
    { count },
    count,
  );
});

const tableHeaders = computed<
  DataTableHeader<AdsAssemblyVideoSettingsEstimationBreakdownItem>[]
>(() => [
  {
    title: t(
      "funnel-flow.paid-social.ads.video.settings.credit-estimation.cost-breakdown.operation",
    ),
    key: "operation",
    sortable: false,
  },
  {
    title: t(
      "funnel-flow.paid-social.ads.video.settings.credit-estimation.cost-breakdown.quantity",
    ),
    key: "quantity",
    sortable: false,
  },
  {
    title: t(
      "funnel-flow.paid-social.ads.video.settings.credit-estimation.cost-breakdown.unit-cost",
    ),
    key: "unitCost",
    sortable: false,
    align: "end",
  },
  {
    title: t(
      "funnel-flow.paid-social.ads.video.settings.credit-estimation.cost-breakdown.subtotal",
    ),
    key: "subtotal",
    sortable: false,
    align: "end",
  },
]);
</script>

<template>
  <AccordionList variant="card">
    <Accordion icon="custom:hi-luca" iconVariant="primary" openByDefault>
      <template #title>
        <span class="tw:text-xl tw:font-bold">
          {{
            $t(
              "funnel-flow.paid-social.ads.video.settings.credit-estimation.title",
            )
          }}
        </span>
      </template>

      <template #description>
        <i18n-t
          keypath="funnel-flow.paid-social.ads.video.settings.credit-estimation.description"
          tag="span"
        >
          <template #ads>{{ adsLabel }}</template>

          <template #totalCost>
            <span class="tw:font-bold">
              {{ formatLucas(estimation.totalCost) }}
            </span>
          </template>

          <template #availableBalance>
            <span class="tw:font-bold">
              {{ formatLucas(estimation.availableBalance) }}
            </span>
          </template>
        </i18n-t>
      </template>

      <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:md:grid-cols-2">
        <AdsAssemblyVideoCreditStatCard
          icon="tabler:atom-2"
          iconVariant="primary"
          :label="
            $t(
              'funnel-flow.paid-social.ads.video.settings.credit-estimation.estimated-total-cost',
              { ads: adsLabel },
            )
          "
          :value="
            estimation.totalCost === undefined
              ? '—'
              : `${formatLucas(estimation.totalCost)} LUCA`
          "
        />

        <AdsAssemblyVideoCreditStatCard
          icon="tabler:wallet"
          iconVariant="success"
          :label="
            $t(
              'funnel-flow.paid-social.ads.video.settings.credit-estimation.available-balance',
            )
          "
          :value="
            estimation.availableBalance === undefined
              ? '—'
              : `${formatLucas(estimation.availableBalance)} LUCA`
          "
        />
      </div>

      <CardBase class="tw:mt-6">
        <VDataTable
          :items="estimation.breakdown"
          :headers="tableHeaders"
          :items-per-page="-1"
          hide-default-footer
        >
          <template #top>
            <div class="tw:p-6">
              <AdsAssemblyVideoLabel icon="tabler:list-details">
                <template #title>
                  {{
                    $t(
                      "funnel-flow.paid-social.ads.video.settings.credit-estimation.cost-breakdown.title",
                    )
                  }}
                </template>
              </AdsAssemblyVideoLabel>
            </div>

            <Separator />
          </template>

          <template #item.unitCost="{ item }">
            {{ item.unitCost.toFixed(2) }} LUCA
          </template>

          <template #item.subtotal="{ item }">
            <span class="tw:font-bold"
              >{{ formatLucas(item.subtotal) }} LUCA</span
            >
          </template>
        </VDataTable>
      </CardBase>

      <Alert
        v-if="estimation.warning"
        type="warning"
        class="tw:mt-4"
        data-testid="video-cost-over-balance"
      >
        {{ estimation.warning }}
      </Alert>

      <p
        v-if="estimation.note"
        class="tw:mt-3 tw:text-sm tw:text-secondary-text"
        data-testid="video-cost-estimate-note"
      >
        {{ estimation.note }}
      </p>
    </Accordion>
  </AccordionList>
</template>
