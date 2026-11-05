<script setup lang="ts">
import { IconCardVariant } from "@/components/cards/IconCard.vue";

defineProps<{
  icon: string;
  iconVariant: IconCardVariant;
  label: string;
  value: string;
}>();
</script>

<template>
  <CardBase borderRadius="md" class="tw:flex tw:items-center tw:gap-3 tw:p-6">
    <IconCard :icon="icon" :variant="iconVariant" size="lg" />

    <div>
      <p class="tw:mb-1 tw:text-sm tw:text-secondary-text">{{ label }}</p>
      <p class="tw:text-xl tw:font-bold">{{ value }}</p>
    </div>
  </CardBase>
</template>
