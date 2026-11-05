<script setup lang="ts">
defineProps<{
  title: string;
  error?: string;
  editable?: boolean;
  // The summary reports the state of the check without offering to fix it
  readonly?: boolean;
}>();
</script>

<template>
  <button
    class="tw:flex tw:w-full tw:flex-wrap tw:justify-between tw:gap-2.5 tw:p-4 tw:text-left"
    type="button"
  >
    <span class="tw:grow tw:font-medium tw:text-secondary-text">
      {{ title }}
    </span>

    <Icon
      v-if="editable && !readonly"
      icon="tabler:pencil"
      class="tw:text-2xl tw:text-gray-500"
    />

    <Chip v-if="error && !readonly" color="warning" variant="label">
      {{ error }}
    </Chip>

    <Icon
      v-if="!error"
      icon="tabler:circle-check-filled"
      class="tw:text-2xl tw:text-success"
    />
    <Icon
      v-else-if="!readonly"
      icon="tabler:alert-triangle"
      class="tw:text-2xl tw:text-warning"
    />
  </button>
</template>
