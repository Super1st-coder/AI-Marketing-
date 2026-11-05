<script setup lang="ts">
import type {
  LucaGuideAdDiagnosisHealth,
  LucaGuideAdDiagnosisSlot,
} from "@/services/guide/LucaGuideAdsApi";

const HEALTH_TONE: Record<
  LucaGuideAdDiagnosisHealth,
  "success" | "warning" | "error" | "info"
> = {
  healthy: "success",
  watch: "info",
  warning: "warning",
};

const props = withDefaults(
  defineProps<{
    isLoading?: boolean;
    card?: LucaGuideAdDiagnosisSlot;
  }>(),
  {
    isLoading: false,
  },
);

const emit = defineEmits<{
  viewInsight: [card: LucaGuideAdDiagnosisSlot];
}>();

function handleViewInsight() {
  if (!props.card) {
    return;
  }

  emit("viewInsight", props.card);
}
</script>

<template>
  <!-- Loading state -->
  <div
    v-if="isLoading"
    class="tw:flex tw:aspect-[3/4] tw:items-center tw:justify-center tw:rounded-2xl tw:border tw:border-gray-300 tw:bg-gray-100"
  >
    <CircleLoader class="tw:text-[30px] tw:text-primary" />
  </div>
  <!-- Card content -->
  <CardBase
    v-else-if="card"
    :shadow="false"
    :outlineColor="HEALTH_TONE[card.health]"
    :borderWidth="2"
    borderRadius="md"
    class="tw:flex tw:flex-col tw:gap-4 tw:p-4"
  >
    <!-- Slot and score -->
    <div
      class="tw:flex tw:items-center tw:justify-between tw:gap-2 tw:font-semibold tw:uppercase"
    >
      <!-- Slot -->
      <span class="tw:text-xs tw:text-secondary-text">
        {{
          $t("luca-guide.ads.detail.diagnosis.slot", {
            number: card.slot_index,
          })
        }}
      </span>

      <!-- Score -->
      <span
        class="tw:text-sm"
        :class="{
          'tw:text-success': card.health === 'healthy',
          'tw:text-info': card.health === 'watch',
          'tw:text-warning': card.health === 'warning',
        }"
      >
        {{ $t("luca-guide.ads.detail.diagnosis.score", { score: card.score }) }}
      </span>
    </div>

    <!-- Title and description -->
    <div>
      <h4 class="tw:mb-1 tw:font-bold">
        {{ card.title }}
      </h4>

      <p class="tw:text-sm tw:text-secondary-text">
        {{ card.headline }}
      </p>
    </div>

    <!-- KPIs and Insight -->
    <div class="tw:flex tw:flex-col tw:gap-2">
      <!-- KPIs -->
      <LucaGuideAdKpiCard
        v-for="kpi in card.kpis"
        :key="kpi.label"
        :label="kpi.label"
        :value="kpi.value"
        :benchmark="kpi.benchmark"
        :status="kpi.status"
      />

      <!-- Insight -->
      <CardBase color="info" softBackground class="tw:px-3 tw:py-2 tw:text-xs">
        <Chip
          v-if="card.recommendation_tag"
          size="sm"
          color="info"
          variant="label"
          leftIcon="tabler:flask"
          class="tw:mb-2 tw:uppercase"
        >
          {{ card.recommendation_tag }}
        </Chip>

        <p class="tw:text-blue-900">{{ card.recommendation }}</p>

        <Link
          is="button"
          type="button"
          class="tw:mt-2 tw:font-medium"
          underline
          color="info-dark"
        >
          {{ $t("luca-guide.ads.detail.diagnosis.see-more") }}
        </Link>
      </CardBase>
    </div>

    <Separator />

    <!-- Actions -->
    <LucaGuideAdInsightCardActions @viewInsight="handleViewInsight" />
  </CardBase>
</template>
