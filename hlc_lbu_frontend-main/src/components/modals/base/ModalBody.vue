<script setup lang="ts">
import { modalScrollableInjectionKey } from "@/components/modals/base/useModalContext";

interface Props {
  paddings?: boolean;
}

withDefaults(defineProps<Props>(), { paddings: true });

const scrollable = inject(
  modalScrollableInjectionKey,
  computed(() => "outer"),
);
</script>

<template>
  <div
    :class="{
      'tw:px-4 tw:sm:px-6': paddings,
      'tw:pb-4 tw:sm:pb-6': scrollable === 'outer' && paddings,
      'tw:py-4 tw:sm:py-6': scrollable === 'inner' && paddings,
      'tw:overflow-y-auto': scrollable === 'inner',
    }"
  >
    <slot />
  </div>
</template>
