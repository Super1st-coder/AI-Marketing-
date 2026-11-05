<script setup lang="ts">
defineProps<{
  label: string;
  value: string | number;
  /** Shown after `/` (e.g. target KPI). */
  target?: string | number;
  /** Shown after `·` (e.g. supporting stat). */
  secondary?: string | number;
}>();
</script>

<template>
  <CardBase borderRadius="lg" class="tw:p-4">
    <p class="tw:mb-2 tw:text-sm tw:text-secondary-text">{{ label }}</p>

    <p class="tw:text-sm tw:leading-tight">
      <span class="tw:text-xl tw:font-bold">
        {{ value }}
      </span>

      <span v-if="target !== undefined" class="tw:text-secondary-text">
        / {{ target }}
      </span>
      <span v-else-if="secondary !== undefined" class="tw:text-secondary-text">
        · {{ secondary }}
      </span>
    </p>
  </CardBase>
</template>
