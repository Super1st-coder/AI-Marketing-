<script setup lang="ts">
export type LucaGuideHomeStatCardColor =
  "default" | "warning" | "success" | "error";

withDefaults(
  defineProps<{
    label: string;
    value: number | string;
    color?: LucaGuideHomeStatCardColor;
  }>(),
  {
    color: "default",
  },
);
</script>

<template>
  <CardBase class="tw:p-4">
    <p
      class="tw:mb-1 tw:text-xs tw:tracking-wider tw:text-secondary-text tw:uppercase"
    >
      {{ label }}
    </p>
    <p
      class="tw:text-3xl tw:font-bold"
      :class="{
        'tw:text-primary-text': color === 'default',
        'tw:text-warning': color === 'warning',
        'tw:text-success': color === 'success',
        'tw:text-error': color === 'error',
      }"
    >
      {{ value }}
    </p>
  </CardBase>
</template>
