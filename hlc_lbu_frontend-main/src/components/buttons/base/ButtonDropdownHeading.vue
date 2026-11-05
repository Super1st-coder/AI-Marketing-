<script setup lang="ts">
withDefaults(
  defineProps<{
    uppercase?: boolean;
  }>(),
  { uppercase: false },
);
</script>

<template>
  <p
    class="tw:py-2 tw:text-xs tw:text-secondary-text tw:first:pt-0"
    :class="{ 'tw:uppercase': uppercase }"
  >
    <slot />
  </p>
</template>
