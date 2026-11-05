<script setup lang="ts">
import type { LucaGuideCampaignAnalysis } from "@/services/guide/LucaGuideCampaignAnalysisApi";
import { LUCA_GUIDE_NORTH_STAR_PRIORITIES } from "@/services/guide/LucaGuideOnboardingApi";
import { CLASSIFICATION_THRESHOLDS } from "@/constants/guide/classification-thresholds";
import type { IconCardVariant } from "@/components/cards/IconCard.vue";

const INSUFFICIENT_DATA_KEY = "insufficient-data" as const;

const PORTFOLIO_CARD_CONFIGS = [
  ...CLASSIFICATION_THRESHOLDS,
  {
    key: INSUFFICIENT_DATA_KEY,
    icon: "tabler:database-off",
    iconVariant: "gray" as IconCardVariant,
  },
];

const props = defineProps<{
  report: LucaGuideCampaignAnalysis;
  versionNumber: number;
  currency?: string;
}>();

const { t, te, locale } = useI18n();

const rangeLabel = computed(() => {
  const start = props.report.date_range_start;
  const end = props.report.date_range_end;

  if (!start || !end) {
    return t("luca-guide.timeframe.max");
  }

  return `${start} → ${end}`;
});

const northStarReadings = computed(() => {
  const readings = props.report.content.north_star_reading ?? [];

  return [...readings].sort(
    (a, b) =>
      LUCA_GUIDE_NORTH_STAR_PRIORITIES.indexOf(a.priority) -
      LUCA_GUIDE_NORTH_STAR_PRIORITIES.indexOf(b.priority),
  );
});

const primaryKpiLabel = computed(() => {
  const key = `luca-guide.kpis.${props.report.primary_kpi_key}.short`;
  return te(key) ? t(key) : props.report.primary_kpi_key;
});

const portfolioCards = computed(() => {
  const state = props.report.content.portfolio_state;
  const breakdownByState = new Map(
    (props.report.content.portfolio_breakdown ?? []).map((entry) => [
      entry.state,
      entry,
    ]),
  );

  return PORTFOLIO_CARD_CONFIGS.map((entry) => {
    const breakdown = breakdownByState.get(entry.key);
    const count =
      breakdown?.count ??
      (entry.key === INSUFFICIENT_DATA_KEY
        ? state.insufficient
        : state[entry.key]);
    let subtext: string | undefined;

    if (breakdown) {
      subtext = t("luca-guide.campaigns.detail.analysis.portfolio.of-spend", {
        spend: formatCurrencyValue(
          breakdown.spend,
          DEFAULT_NUMBER_LOCALE,
          props.currency,
        ),
        percent: formatPercentValue(breakdown.pct_spend, DEFAULT_NUMBER_LOCALE),
      });
    }

    return {
      key: entry.key,
      icon: entry.icon,
      iconVariant: entry.iconVariant,
      title: t(`luca-guide.campaigns.detail.analysis.portfolio.${entry.key}`, {
        count,
      }),
      subtext,
    };
  });
});

function getNorthStarPriorityLabel(
  priority: (typeof LUCA_GUIDE_NORTH_STAR_PRIORITIES)[number],
) {
  return t(`luca-guide.campaigns.detail.analysis.north-star.${priority}`);
}

function getNorthStarCurrentVs(item: (typeof northStarReadings.value)[number]) {
  const key =
    item.priority === "primary"
      ? "luca-guide.campaigns.detail.analysis.north-star.current-vs-target"
      : "luca-guide.campaigns.detail.analysis.north-star.current-vs-guardrail";

  return t(key, {
    value: item.value,
    target: item.target,
  });
}

function formatAdSetCost(value: number | null) {
  if (value == null) {
    return "—";
  }

  return formatCurrencyValue(value, locale.value, props.currency);
}

function getAdSetMetrics(
  adSet: LucaGuideCampaignAnalysis["content"]["ad_sets"][number],
) {
  const spend = formatCurrencyValue(adSet.spend, locale.value, props.currency);
  const cost = formatAdSetCost(adSet.cost_per_result);
  const kpi = primaryKpiLabel.value;

  if (adSet.results == null) {
    return t(
      "luca-guide.campaigns.detail.analysis.ad-sets.metrics-without-results",
      { spend, kpi, cost },
    );
  }

  return t("luca-guide.campaigns.detail.analysis.ad-sets.metrics", {
    spend,
    results: t("luca-guide.campaigns.detail.analysis.ad-sets.results", {
      count: adSet.results,
    }),
    kpi,
    cost,
  });
}

const reportBodyRef = ref<HTMLElement>();

function getShareContent() {
  const el = reportBodyRef.value;

  return {
    html: el ? `<html><body>${el.innerHTML}</body></html>` : "",
    text: el?.innerText.trim() ?? "",
  };
}

async function handleCopyToClipboard() {
  const { html, text } = getShareContent();

  try {
    await navigator.clipboard.write([
      new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" }),
      }),
    ]);
  } catch (error) {
    console.error("Failed to copy campaign analysis:", error);

    try {
      await navigator.clipboard.writeText(text);
    } catch (fallbackError) {
      console.error(
        "Failed to copy campaign analysis as plain text:",
        fallbackError,
      );
    }
  }
}

function handleShareEmail() {
  const { text } = getShareContent();
  const subject = t("luca-guide.campaigns.detail.analysis.share-subject", {
    range: rangeLabel.value,
  });

  window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(text)}`;
}

function handleShareWhatsApp() {
  const { text } = getShareContent();

  window.open(
    `https://wa.me/?text=${encodeURIComponent(text)}`,
    "_blank",
    "noopener,noreferrer",
  );
}
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-5">
    <!-- Header with version and share button -->
    <div
      class="tw:flex tw:flex-wrap tw:items-center tw:justify-between tw:gap-2"
    >
      <!-- Version and date range -->
      <p class="tw:text-sm tw:text-secondary-text">
        {{
          $t("luca-guide.campaigns.detail.analysis.version", {
            versionNumber,
            range: rangeLabel,
          })
        }}
      </p>

      <!-- Share button -->
      <ButtonDropdown
        type="button"
        variant="text"
        color="secondary"
        size="sm"
        leftIcon="tabler:share"
        keepTextVariantPadding
        :shadow="false"
        noContentPadding
      >
        {{ $t("luca-guide.campaigns.detail.analysis.share") }}

        <template #options>
          <ButtonDropdownOption
            leftIcon="tabler:mail"
            @click="handleShareEmail"
          >
            {{ $t("luca-guide.campaigns.detail.analysis.email") }}
          </ButtonDropdownOption>

          <ButtonDropdownOption
            leftIcon="tabler:brand-whatsapp"
            @click="handleShareWhatsApp"
          >
            {{ $t("luca-guide.campaigns.detail.analysis.whatsapp") }}
          </ButtonDropdownOption>

          <ButtonDropdownOption
            leftIcon="tabler:copy"
            @click="handleCopyToClipboard"
          >
            {{ $t("luca-guide.campaigns.detail.analysis.copy-to-clipboard") }}
          </ButtonDropdownOption>
        </template>
      </ButtonDropdown>
    </div>

    <div ref="reportBodyRef" class="tw:flex tw:flex-col tw:gap-5">
      <!-- Stand's headline -->
      <div
        class="tw:rounded-xl tw:border tw:border-gray-300 tw:bg-gray-100 tw:p-4"
      >
        <p class="tw:bg-text-600 tw:mb-1 tw:text-sm tw:font-bold">
          {{
            $t("luca-guide.campaigns.detail.analysis.stands.title", {
              range: rangeLabel,
            })
          }}
        </p>

        <p class="tw:bg-text-600 tw:text-sm">{{ report.content.headline }}</p>
      </div>

      <Separator />

      <!-- PORTFOLIO STATE · ADS × SPEND × RESULTS -->
      <section class="tw:flex tw:flex-col tw:gap-4">
        <!-- Cards  -->
        <section class="tw:flex tw:flex-col tw:gap-4">
          <h3
            class="tw:text-sm tw:font-bold tw:text-secondary-text tw:uppercase"
          >
            {{ $t("luca-guide.campaigns.detail.analysis.portfolio.title") }}
          </h3>

          <div
            class="tw:grid tw:grid-cols-1 tw:gap-5 tw:sm:grid-cols-2 tw:lg:grid-cols-3"
          >
            <CardBase
              v-for="card in portfolioCards"
              :key="card.key"
              :shadow="false"
              borderRadius="md"
              class="tw:flex tw:flex-col tw:gap-3 tw:p-4"
            >
              <div class="tw:flex tw:items-center tw:gap-3">
                <IconCard
                  :icon="card.icon"
                  :variant="card.iconVariant"
                  size="md"
                />

                <p class="tw:text-lg tw:font-bold">{{ card.title }}</p>
              </div>

              <p v-if="card.subtext" class="tw:text-sm tw:text-secondary-text">
                {{ card.subtext }}
              </p>
            </CardBase>
          </div>
        </section>

        <!-- Objective & delivery reading -->
        <CardBase
          is="section"
          :shadow="false"
          borderRadius="md"
          class="tw:p-5 tw:text-sm"
        >
          <h3
            class="tw:mb-2 tw:flex tw:items-center tw:gap-2 tw:text-sm tw:font-semibold tw:uppercase"
          >
            <Icon icon="tabler:target" class="tw:text-lg tw:text-primary" />

            <span>
              {{ $t("luca-guide.campaigns.detail.analysis.objective.title") }}
            </span>
          </h3>

          <p class="tw:text-secondary-text">
            {{ report.content.objective_reading }}
          </p>
        </CardBase>

        <!-- North star reading -->
        <CardBase
          is="section"
          :shadow="false"
          borderRadius="md"
          class="tw:p-5 tw:text-sm"
        >
          <h3
            class="tw:mb-2 tw:flex tw:items-center tw:gap-2 tw:text-sm tw:font-semibold tw:uppercase"
          >
            <Icon icon="custom:hi-luca" class="tw:text-lg tw:text-primary" />

            <span>
              {{ $t("luca-guide.campaigns.detail.analysis.north-star.title") }}
            </span>
          </h3>

          <ul
            v-if="northStarReadings.length"
            class="tw:flex tw:list-disc tw:flex-col tw:gap-3 tw:pl-4 tw:text-secondary-text"
          >
            <li v-for="item in northStarReadings" :key="item.priority">
              <strong>
                {{
                  $t(
                    "luca-guide.campaigns.detail.analysis.north-star.item-label",
                    {
                      priority: getNorthStarPriorityLabel(item.priority),
                      kpi: item.kpi,
                    },
                  )
                }}:
              </strong>

              <span>{{ getNorthStarCurrentVs(item) }}. {{ item.reading }}</span>
            </li>
          </ul>

          <!-- Empty state -->
          <template v-else>
            <p class="tw:text-secondary-text">
              {{ $t("luca-guide.campaigns.detail.analysis.north-star.empty") }}
            </p>
          </template>
        </CardBase>

        <!-- Cause & effect synthesis -->
        <CardBase
          is="section"
          :shadow="false"
          borderRadius="md"
          class="tw:p-5 tw:text-sm"
        >
          <h3
            class="tw:mb-2 tw:flex tw:items-center tw:gap-2 tw:text-sm tw:font-semibold tw:uppercase"
          >
            <Icon icon="tabler:history" class="tw:text-lg tw:text-primary" />
            {{ $t("luca-guide.campaigns.detail.analysis.synthesis.title") }}
          </h3>

          <p class="tw:text-secondary-text">
            {{ report.content.constraint_synthesis }}
          </p>
        </CardBase>
      </section>

      <!-- Ad set readings -->
      <section class="tw:flex tw:flex-col tw:gap-4">
        <h3 class="tw:text-sm tw:font-bold tw:text-secondary-text tw:uppercase">
          {{ $t("luca-guide.campaigns.detail.analysis.ad-sets.title") }}
        </h3>

        <template v-if="report.content.ad_sets?.length">
          <!-- Ad set card -->
          <CardBase
            v-for="adSet in report.content.ad_sets"
            :key="adSet.name"
            color="primary"
            outlineColor="primary"
            softBackground
            :shadow="false"
            borderRadius="md"
            class="tw:flex tw:flex-col tw:gap-2 tw:px-4 tw:py-5 tw:text-sm"
          >
            <div
              class="tw:flex tw:flex-col tw:gap-1 tw:lg:flex-row tw:lg:items-start tw:lg:justify-between tw:lg:gap-4"
            >
              <p class="tw:font-semibold tw:text-primary">{{ adSet.name }}</p>

              <p class="tw:shrink-0 tw:text-secondary-text">
                {{ getAdSetMetrics(adSet) }}
              </p>
            </div>

            <p class="tw:text-secondary-text">{{ adSet.reading }}</p>
          </CardBase>
        </template>

        <!-- Empty state -->
        <CardBase
          v-else
          :shadow="false"
          borderRadius="md"
          class="tw:p-5 tw:text-sm"
        >
          <p class="tw:text-secondary-text">
            {{ $t("luca-guide.campaigns.detail.analysis.ad-sets.empty") }}
          </p>
        </CardBase>
      </section>

      <!-- Notice -->
      <Alert type="info" softBackground>
        <template #title>
          {{ $t("luca-guide.campaigns.detail.analysis.notice.title") }}
        </template>
        {{ $t("luca-guide.campaigns.detail.analysis.notice.description") }}
      </Alert>

      <!-- Footer -->
      <p class="tw:text-sm tw:text-secondary-text tw:italic">
        {{
          $t("luca-guide.campaigns.detail.analysis.footer", {
            range: rangeLabel,
          })
        }}
      </p>
    </div>
  </div>
</template>
