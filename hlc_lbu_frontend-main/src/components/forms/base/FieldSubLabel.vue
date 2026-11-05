<script lang="ts" setup>
interface Props {
  error?: boolean;
}

defineProps<Props>();
</script>

<template>
  <label
    class="tw:text-[14px]"
    :class="{
      'tw:text-primary-text': !error,
      'tw:text-error': error,
    }"
  >
    <slot />
  </label>
</template>
