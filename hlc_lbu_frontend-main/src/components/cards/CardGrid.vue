<script lang="ts" setup>
export interface CardGridProps {
  columns?: 3 | 4;
}

withDefaults(defineProps<CardGridProps>(), { columns: 3 });
</script>

<template>
  <div
    class="tw:grid tw:gap-5"
    :class="{
      'tw:lg:grid-cols-2 tw:xl:grid-cols-3': columns === 3,
      'tw:lg:grid-cols-2 tw:xl:grid-cols-4': columns === 4,
    }"
  >
    <slot />
  </div>
</template>
