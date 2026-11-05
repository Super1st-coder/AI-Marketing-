<script setup lang="ts">
import { IconCardVariant } from "@/components/cards/IconCard.vue";

defineProps<{ icon: string; iconVariant: IconCardVariant }>();
</script>

<template>
  <CardBase class="tw:grid tw:grid-cols-1 tw:gap-6 tw:p-6">
    <div class="tw:flex tw:items-center tw:gap-3">
      <IconCard :icon="icon" :variant="iconVariant" size="lg" />

      <div>
        <h2 class="tw:mb-1 tw:text-xl tw:font-bold">
          <slot name="title" />
        </h2>

        <p class="tw:text-sm tw:text-secondary-text">
          <slot name="description" />
        </p>
      </div>
    </div>

    <slot />
  </CardBase>
</template>
