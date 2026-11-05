<script lang="ts" setup>
export interface Props {
  icon?: string;
}

defineProps<Props>();
</script>

<template>
  <button type="button">
    <Icon v-if="icon" :icon="icon" class="tw:text-xl" />
  </button>
</template>
