<script lang="ts" setup>
import { type Component } from "vue";

export interface LinkBaseProps {
  is?: string | Component;
  icon?: string;
  leftIcon?: string;
  underline?: boolean;
  color?:
    | "primary"
    | "secondary"
    | "success"
    | "warning"
    | "error"
    | "info"
    | "info-dark";
  disabled?: boolean;
}

withDefaults(defineProps<LinkBaseProps>(), {
  is: "a",
  color: "primary",
});
</script>

<template>
  <component
    :is="is"
    class="tw:cursor-pointer tw:text-left tw:underline-offset-2 tw:hover:underline"
    :class="{
      'tw:inline-flex tw:items-center tw:gap-2': leftIcon || icon,
      'tw:underline': underline,
      'tw:text-primary': color === 'primary',
      'tw:text-secondary': color === 'secondary',
      'tw:text-success': color === 'success',
      'tw:text-warning': color === 'warning',
      'tw:text-error-500': color === 'error',
      'tw:text-blue': color === 'info',
      'tw:text-blue-900': color === 'info-dark',

      'tw:pointer-events-none tw:opacity-50': disabled,
    }"
    :disabled="disabled"
  >
    <Icon v-if="leftIcon" :icon="leftIcon" class="tw:text-[1.43em]" />

    <slot />

    <Icon v-if="icon" :icon="icon" class="tw:text-[1.43em]" />
  </component>
</template>
