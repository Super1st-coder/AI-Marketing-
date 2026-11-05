<script setup lang="ts">
import LucaGuideCampaignAnalysisApi, {
  type LucaGuideCampaignAnalysis,
} from "@/services/guide/LucaGuideCampaignAnalysisApi";
import type { LucaGuideTimeframe } from "@/components/guide/LucaGuideTimeFilters.vue";

const props = defineProps<{
  campaignId: string;
  currency?: string;
}>();

const { t, locale } = useI18n();

const timeframe = ref<LucaGuideTimeframe>({ type: "days", days: 7 });
const isGenerating = ref(false);
const reports = ref(await LucaGuideCampaignAnalysisApi.list(props.campaignId));
const currentReport = ref<LucaGuideCampaignAnalysis>();

const historyReports = computed(() =>
  [...reports.value].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  ),
);

function reportVersion(index: number) {
  return historyReports.value.length - index;
}

function reportDateRangeLabel(report: LucaGuideCampaignAnalysis) {
  if (!report.date_range_start || !report.date_range_end) {
    return t("luca-guide.timeframe.max");
  }

  return formatDateRange(
    new Date(`${report.date_range_start}T00:00:00`),
    new Date(`${report.date_range_end}T00:00:00`),
    locale.value,
  );
}

function getSelectedDateRange(next: LucaGuideTimeframe) {
  if (next.type === "max") {
    return {
      date_range_start: null,
      date_range_end: null,
    };
  }

  if (next.type === "custom-range") {
    return {
      date_range_start: next.startDate,
      date_range_end: next.endDate,
    };
  }

  const end = new Date();
  end.setHours(0, 0, 0, 0);

  const start = new Date(end);
  start.setDate(start.getDate() - next.days);

  return {
    date_range_start: formatLocalIsoDate(start),
    date_range_end: formatLocalIsoDate(end),
  };
}

async function handleGenerateReport() {
  const range = getSelectedDateRange(timeframe.value);
  isGenerating.value = true;

  try {
    const report = await LucaGuideCampaignAnalysisApi.generate(
      props.campaignId,
      range.date_range_start && range.date_range_end
        ? {
            date_range_start: range.date_range_start,
            date_range_end: range.date_range_end,
          }
        : {},
    );

    currentReport.value = report;
    reports.value.unshift(report);
  } catch (error) {
    console.error("Failed to generate campaign analysis:", error);
    throw error;
  } finally {
    isGenerating.value = false;
  }
}

function timeframeFromReport(
  report: LucaGuideCampaignAnalysis,
): LucaGuideTimeframe {
  if (!report.date_range_start || !report.date_range_end) {
    return { type: "max" };
  }

  const today = formatLocalIsoDate(new Date());
  const start = new Date(`${report.date_range_start}T00:00:00`);
  const end = new Date(`${report.date_range_end}T00:00:00`);
  const days = Math.max(
    1,
    Math.round((end.getTime() - start.getTime()) / 86_400_000),
  );

  if (report.date_range_end === today && [7, 14, 30].includes(days)) {
    return { type: "days", days };
  }

  return {
    type: "custom-range",
    startDate: report.date_range_start,
    endDate: report.date_range_end,
  };
}

function handleSelectReport(report: LucaGuideCampaignAnalysis) {
  currentReport.value = report;
  timeframe.value = timeframeFromReport(report);
}

const currentVersionNumber = computed(() => {
  if (!currentReport.value) {
    return 0;
  }

  const index = historyReports.value.findIndex(
    (item) => item.id === currentReport.value?.id,
  );

  if (index === -1) {
    return historyReports.value.length;
  }

  return reportVersion(index);
});
</script>

<template>
  <AccordionList variant="card">
    <Accordion titleClass="tw:text-lg tw:font-bold">
      <template #icon>
        <IconCard icon="tabler:file-search" variant="primary" size="lg" />
      </template>

      <template #title>
        {{ $t("luca-guide.campaigns.detail.analysis.title") }}
      </template>

      <template #description>
        {{ $t("luca-guide.campaigns.detail.analysis.description") }}
      </template>

      <div class="tw:flex tw:flex-col tw:gap-5">
        <div
          class="tw:flex tw:flex-col tw:items-end tw:justify-between tw:gap-3 tw:xl:flex-row"
        >
          <LucaGuideTimeFilters
            v-model="timeframe"
            :options="[7, 14, 30, 'custom-range', 'max']"
            :disabled="isGenerating"
          />

          <div class="tw:flex tw:shrink-0 tw:items-center tw:gap-2">
            <Button
              :leftIcon="currentReport ? 'tabler:refresh' : 'custom:hi-luca'"
              :isLoading="isGenerating"
              @click="handleGenerateReport"
            >
              {{
                $t(
                  currentReport
                    ? "luca-guide.campaigns.detail.analysis.re-run"
                    : "luca-guide.campaigns.detail.analysis.button",
                )
              }}
            </Button>

            <ButtonDropdown
              type="button"
              variant="outlined"
              color="secondary"
              leftIcon="tabler:history"
              noContentPadding
              :disabled="isGenerating || !reports.length"
            >
              {{ $t("luca-guide.history") }}

              <template #options>
                <ButtonDropdownOption
                  v-for="(report, index) in historyReports"
                  :key="report.id"
                  :selected="currentReport?.id === report.id"
                  @click="handleSelectReport(report)"
                >
                  <i18n-t
                    keypath="luca-guide.campaigns.detail.analysis.history.item"
                    tag="span"
                  >
                    <template #versionNumber>
                      {{ reportVersion(index) }}
                    </template>
                    <template #range>
                      <span>
                        {{ reportDateRangeLabel(report) }}
                      </span>
                    </template>
                  </i18n-t>
                </ButtonDropdownOption>
              </template>
            </ButtonDropdown>
          </div>
        </div>

        <LucaGuideCampaignDetailAnalysisContent
          v-if="currentReport"
          :report="currentReport"
          :versionNumber="currentVersionNumber"
          :currency="currency"
        />
        <LucaGuideEmptyState
          v-else
          icon="tabler:chart-line"
          :maxWidth="330"
          :title="$t('luca-guide.campaigns.detail.analysis.empty.title')"
          :description="
            $t('luca-guide.campaigns.detail.analysis.empty.description')
          "
        />
      </div>
    </Accordion>
  </AccordionList>
</template>
