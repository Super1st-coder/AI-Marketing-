<script setup lang="ts">
// Three dots that pulse one after the other, after a text that's still in
// progress. They take the text's color. Decorative only
</script>

<template>
  <span class="tw:inline-flex tw:gap-0.5" aria-hidden="true">
    <span
      v-for="index in 3"
      :key="index"
      class="dot tw:size-1 tw:rounded-full tw:bg-current"
      :style="{ animationDelay: `${(index - 1) * 0.2}s` }"
    />
  </span>
</template>

<style scoped>
.dot {
  animation: dot-pulse 1.2s infinite ease-in-out;
}

@keyframes dot-pulse {
  0%,
  100% {
    opacity: 0.3;
  }
  50% {
    opacity: 1;
  }
}
</style>
