<script setup lang="ts">
interface Props {
  type?: "horizontal" | "vertical";
}

withDefaults(defineProps<Props>(), { type: "horizontal" });
</script>

<template>
  <hr
    class="tw:border-none tw:bg-gray-300"
    :class="{
      'tw:h-px tw:w-full': type === 'horizontal',
      'tw:h-full tw:w-px': type === 'vertical',
    }"
  />
</template>
