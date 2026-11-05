<script setup lang="ts">
interface Props {
  variant?: "normal" | "light";
}

defineProps<Props>();
</script>

<template>
  <p
    class="tw:whitespace-pre-line"
    :class="{
      'tw:text-primary-text/55': variant === 'light',
    }"
  >
    <slot />
  </p>
</template>
