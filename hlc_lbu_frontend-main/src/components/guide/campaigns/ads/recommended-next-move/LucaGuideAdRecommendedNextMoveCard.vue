<script setup lang="ts">
import type { LucaGuideAdDiagnosisKpi } from "@/services/guide/LucaGuideAdsApi";
import type { CardBaseColor } from "@/components/cards/base/CardBase.vue";

export type LucaGuideAdRecommendedNextMoveTone = Extract<
  CardBaseColor,
  "primary" | "success" | "warning" | "info"
>;

export type LucaGuideAdRecommendedNextMoveCardData = {
  id: string;
  category: string;
  icon: string;
  title: string;
  description: string;
  kpis: LucaGuideAdDiagnosisKpi[];
  actionLabel: string;
  tone: LucaGuideAdRecommendedNextMoveTone;
  recommendation: string;
  calibrationWarning: string | null;
  diagnosis: string;
  evidence: string;
  riskOfNotActing: string;
  successCriteria: string;
};

const props = defineProps<{
  card: LucaGuideAdRecommendedNextMoveCardData;
}>();

const emit = defineEmits<{
  viewInsight: [card: LucaGuideAdRecommendedNextMoveCardData];
}>();

function handleViewInsight() {
  if (!props.card) {
    return;
  }

  emit("viewInsight", props.card);
}
</script>

<template>
  <CardBase
    :shadow="false"
    borderRadius="md"
    class="tw:flex tw:flex-col tw:gap-4 tw:p-4"
  >
    <!-- Title and description -->
    <div>
      <!-- Category -->
      <p
        class="tw:mb-1 tw:flex tw:items-center tw:gap-2 tw:text-secondary-text"
      >
        <Icon :icon="card.icon" class="tw:text-[16px]" />
        <span class="tw:text-xs tw:font-semibold tw:uppercase">{{
          card.category
        }}</span>
      </p>

      <h4 class="tw:mb-1 tw:font-bold">
        {{ card.title }}
      </h4>

      <p class="tw:text-sm tw:text-secondary-text">
        {{ card.description }}
      </p>
    </div>

    <!-- KPIs and Insight -->
    <div class="tw:flex tw:flex-col tw:gap-2">
      <LucaGuideAdKpiCard
        v-for="kpi in card.kpis"
        :key="kpi.label"
        :label="kpi.label"
        :value="kpi.value"
        :benchmark="kpi.benchmark"
        :status="kpi.status"
      />

      <Alert v-if="card.calibrationWarning" type="warning" class="tw:text-xs">
        {{ card.calibrationWarning }}
      </Alert>

      <CardBase
        v-if="card.recommendation"
        :color="card.tone"
        :outlineColor="card.tone"
        softBackground
        class="tw:px-3 tw:py-2"
      >
        <Chip
          v-if="card.actionLabel"
          size="sm"
          :color="card.tone"
          variant="label"
          uppercase
          class="tw:mb-2"
        >
          {{ card.actionLabel }}
        </Chip>

        <p
          class="tw:text-xs tw:font-medium"
          :class="{
            'tw:text-primary-800': card.tone === 'primary',
            'tw:text-success-800': card.tone === 'success',
            'tw:text-warning-900': card.tone === 'warning',
            'tw:text-blue-900': card.tone === 'info',
          }"
        >
          {{ card.recommendation }}
        </p>
      </CardBase>
    </div>

    <Separator />

    <!-- Actions -->
    <LucaGuideAdInsightCardActions @viewInsight="handleViewInsight" />
  </CardBase>
</template>
