<script setup lang="ts">
import { useTabsContext } from "./useTabsContext";

const tabsContext = useTabsContext();

const variant = computed(() => tabsContext?.variant.value ?? "default");
const alignment = computed(() => tabsContext?.alignment.value ?? "start");
</script>

<template>
  <div
    class="tw:flex tw:overflow-x-auto"
    :class="{
      'tw:justify-start': alignment === 'start',
      'tw:justify-center': alignment === 'center',
      'tw:justify-end': alignment === 'end',

      // Default variant
      'tw:border-b tw:border-gray-300': variant === 'default',

      // Button group variant
      'tw:gap-1 tw:rounded-xl tw:border-2 tw:border-gray-200 tw:bg-[#F7F5F3] tw:p-1':
        variant === 'buttonGroup',
    }"
  >
    <slot />
  </div>
</template>
