<script setup lang="ts">
defineProps<{
  icon: string;
  title: string;
  description: string;
  time: string;
}>();
</script>

<template>
  <div class="tw:flex tw:items-start tw:gap-3 tw:py-4">
    <div
      class="tw:flex tw:h-9 tw:w-9 tw:shrink-0 tw:items-center tw:justify-center tw:rounded-md tw:bg-gray-100"
    >
      <Icon :icon="icon" class="tw:text-[24px] tw:text-gray-400" />
    </div>

    <div class="tw:min-w-0 tw:grow">
      <p class="tw:truncate tw:text-sm tw:font-semibold">{{ title }}</p>
      <p class="tw:text-xs tw:text-secondary-text">{{ description }}</p>
    </div>

    <p class="tw:shrink-0 tw:text-xs tw:text-secondary-text">{{ time }}</p>
  </div>
</template>
