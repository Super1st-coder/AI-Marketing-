<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string;
    description: string;
    icon?: string;
    maxWidth?: number;
  }>(),
  {
    icon: "tabler:bell-off",
    maxWidth: 300,
  },
);
</script>

<template>
  <div
    class="tw:flex tw:h-full tw:flex-col tw:items-center tw:justify-center tw:px-6 tw:py-8 tw:text-center"
  >
    <IconCard :icon="icon" variant="gray" size="lg" class="tw:mb-6" />

    <h3 class="tw:mb-3 tw:font-semibold">
      {{ title }}
    </h3>

    <p
      class="tw:text-sm tw:text-secondary-text"
      :class="{ 'tw:mb-6': $slots.default }"
      :style="{ maxWidth: `${maxWidth}px` }"
    >
      {{ description }}
    </p>

    <slot />
  </div>
</template>
