<script lang="ts" setup>
defineProps<{
  disableMargin?: boolean;
}>();
</script>

<template>
  <div
    class="tw:text-sm tw:leading-tight tw:text-error"
    :class="{ 'tw:mt-2': !disableMargin }"
  >
    <slot />
  </div>
</template>
