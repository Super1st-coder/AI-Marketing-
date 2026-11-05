<script lang="ts" setup>
defineProps<{
  icon: string;
}>();
</script>

<template>
  <button class="tw:p-2">
    <Icon class="tw:text-[22px] tw:text-secondary-text" :icon="icon" />
  </button>
</template>
