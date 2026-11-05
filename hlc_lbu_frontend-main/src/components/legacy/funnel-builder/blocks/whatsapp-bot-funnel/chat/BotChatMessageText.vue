<script lang="ts" setup>
interface Props {
  type?: "normal" | "option";
}

withDefaults(defineProps<Props>(), { type: "normal" });
</script>

<template>
  <p
    class="tw:rounded-md tw:p-2 tw:text-sm tw:whitespace-break-spaces"
    :class="{
      'tw:bg-snackbar tw:text-white': type === 'normal',
      'tw:bg-outline-border tw:text-primary-text': type === 'option',
    }"
  >
    <slot />
  </p>
</template>
