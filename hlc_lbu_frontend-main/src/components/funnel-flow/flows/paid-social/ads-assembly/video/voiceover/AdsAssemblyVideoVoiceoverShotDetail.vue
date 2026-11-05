<script setup lang="ts">
defineProps<{ title: string }>();
</script>

<template>
  <div>
    <p
      class="tw:mb-1 tw:text-xs tw:font-semibold tw:text-gray-400 tw:uppercase"
    >
      {{ title }}
    </p>

    <p class="tw:text-sm">
      <slot />
    </p>
  </div>
</template>
