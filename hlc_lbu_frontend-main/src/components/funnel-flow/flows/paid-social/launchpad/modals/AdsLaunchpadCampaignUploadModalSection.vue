<script setup lang="ts">
withDefaults(defineProps<{ mode?: "row" | "col" }>(), { mode: "row" });
</script>

<template>
  <div
    class="tw:gap-2"
    :class="{
      'tw:grid tw:grid-cols-1 tw:md:grid-cols-2': mode === 'row',
      'tw:grid tw:grid-cols-1': mode === 'col',
    }"
  >
    <div class="tw:font-medium"><slot name="label" /></div>

    <div
      class="tw:text-secondary-text"
      :class="{ 'tw:justify-self-end': mode === 'row' }"
    >
      <slot />
    </div>
  </div>
</template>
