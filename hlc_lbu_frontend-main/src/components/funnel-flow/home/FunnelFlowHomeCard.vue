<script lang="ts" setup>
defineProps<{
  icon: string;
}>();
</script>

<template>
  <CardBase class="tw:flex tw:flex-col tw:items-center tw:p-6 tw:text-center">
    <div
      class="tw:mb-8 tw:flex tw:h-32 tw:w-32 tw:items-center tw:justify-center tw:rounded-full tw:bg-primary/8 tw:text-[64px] tw:text-primary/38"
    >
      <Icon :icon="icon" />
    </div>

    <h2 class="tw:mb-5 tw:text-xl tw:font-extrabold">
      <slot name="title" />
    </h2>

    <p class="tw:mb-11 tw:text-secondary">
      <slot name="description" />
    </p>

    <slot name="action" />
  </CardBase>
</template>
