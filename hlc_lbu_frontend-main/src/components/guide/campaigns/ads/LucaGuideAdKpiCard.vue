<script setup lang="ts">
import type { LucaGuideAdDiagnosisKpiStatus } from "@/services/guide/LucaGuideAdsApi";

const props = withDefaults(
  defineProps<{
    label: string;
    value: string;
    benchmark?: string | null;
    status?: LucaGuideAdDiagnosisKpiStatus;
    stacked?: boolean;
  }>(),
  {
    stacked: false,
  },
);

const showBenchmark = computed(() => {
  const benchmark = props.benchmark?.trim();
  if (!benchmark) {
    return false;
  }

  return benchmark.toUpperCase() !== "N/A";
});

const valueClass = computed(() => ({
  "tw:text-success": props.status === "good",
  "tw:text-error": props.status === "bad",
}));
</script>

<template>
  <div class="tw:rounded-xl tw:border tw:border-gray-200 tw:px-3 tw:py-2">
    <p
      class="tw:mb-1 tw:text-xs tw:font-semibold tw:text-secondary-text tw:uppercase"
    >
      {{ label }}
    </p>

    <p v-if="!stacked">
      <span class="tw:text-xl tw:font-bold" :class="valueClass">
        {{ value }}
      </span>
      <template v-if="showBenchmark">
        {{ " " }}
        <span class="tw:text-xs tw:text-secondary-text">
          {{ ` / ${benchmark}` }}
        </span>
      </template>
    </p>

    <template v-else>
      <p class="tw:text-xl tw:font-bold" :class="valueClass">
        {{ value }}
      </p>

      <p v-if="showBenchmark" class="tw:mt-1 tw:text-xs tw:text-secondary-text">
        {{ benchmark }}
      </p>
    </template>
  </div>
</template>
