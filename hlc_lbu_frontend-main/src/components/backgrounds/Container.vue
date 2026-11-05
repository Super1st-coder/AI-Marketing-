<script lang="ts" setup>
export interface ContainerProps {
  maxWidth?: string | number;
}

withDefaults(defineProps<ContainerProps>(), { maxWidth: 1160 });
</script>

<template>
  <div
    class="tw:container tw:mx-auto tw:px-4"
    :style="{
      maxWidth: typeof maxWidth === 'number' ? `${maxWidth + 32}px` : maxWidth,
    }"
  >
    <slot />
  </div>
</template>
