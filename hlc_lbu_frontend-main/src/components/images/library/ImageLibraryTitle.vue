<script setup lang="ts">
defineProps<{
  icon?: string;
}>();
</script>

<template>
  <h2
    class="tw:flex tw:items-center tw:gap-2 tw:p-6 tw:pr-[72px] tw:text-2xl tw:font-bold"
  >
    <Icon v-if="icon" :icon="icon" class="tw:text-3xl" />

    <span class="tw:font-bold">
      <slot />
    </span>
  </h2>
</template>
