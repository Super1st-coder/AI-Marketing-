<script setup lang="ts">
import {
  accordionListInjectionKey,
  AccordionVariant,
} from "./useAccordionContext";

interface AccordionListProps {
  variant?: AccordionVariant;
}

const props = withDefaults(defineProps<AccordionListProps>(), {
  variant: "default",
});

provide(accordionListInjectionKey, {
  variant: computed(() => props.variant),
});
</script>

<template>
  <div
    class="tw:grid tw:grid-cols-1"
    :class="{
      'tw:gap-2': variant === 'default',
      'tw:gap-5': variant === 'card',
      'tw:divide-y tw:divide-divider':
        variant === 'text' || variant === 'solid',
    }"
  >
    <slot />
  </div>
</template>
