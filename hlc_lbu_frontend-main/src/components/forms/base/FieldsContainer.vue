<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    spacing?: "sm" | "md" | "lg";
  }>(),
  {
    spacing: "lg",
  },
);

const spacingClass = computed(() => ({
  "tw:gap-3": props.spacing === "sm",
  "tw:gap-4": props.spacing === "md",
  "tw:gap-6": props.spacing === "lg",
}));
</script>

<template>
  <div class="tw:flex tw:flex-col" :class="spacingClass">
    <slot />
  </div>
</template>
