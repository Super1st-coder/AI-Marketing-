<script setup lang="ts">
withDefaults(
  defineProps<{
    columns?: 3 | 4 | 5;
  }>(),
  {
    columns: 5,
  },
);
</script>

<template>
  <div
    class="tw:grid tw:grid-cols-1 tw:gap-5"
    :class="{
      'tw:md:grid-cols-3': columns === 3,
      'tw:md:grid-cols-4': columns === 4,
      'tw:md:grid-cols-5': columns === 5,
    }"
  >
    <slot />
  </div>
</template>
