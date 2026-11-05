<script lang="ts" setup>
interface Props {
  required?: boolean;
}

defineProps<Props>();
</script>

<template>
  <span
    class="tw:mt-2 tw:inline-block tw:text-sm tw:leading-tight tw:font-normal tw:text-gray-500"
  >
    <slot />
  </span>
</template>
