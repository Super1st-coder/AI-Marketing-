<script lang="ts">
export const iconCardVariants = [
  "none",
  "primary",
  "gray",
  "info",
  "warning",
  "success",
  "error",
] as const;

export type IconCardVariant = (typeof iconCardVariants)[number];
</script>

<script setup lang="ts">
export interface IconCardProps {
  src?: string;
  color?: string;
  size?: "sm" | "md" | "lg";
  icon?: string;
  variant?: IconCardVariant;
}

withDefaults(defineProps<IconCardProps>(), { size: "md" });
</script>

<template>
  <div
    class="tw:inline-flex tw:aspect-square tw:rounded-md"
    :class="{
      'tw:p-[5px]': size === 'sm',
      'tw:p-2': size === 'md',
      'tw:p-[12px]': size === 'lg',
      'tw:bg-primary/16 tw:text-primary': variant === 'primary',
      'tw:bg-secondary/16 tw:text-secondary': variant === 'gray',
      'tw:bg-info-light tw:text-info': variant === 'info',
      'tw:bg-warning-light tw:text-warning': variant === 'warning',
      'tw:bg-success-light tw:text-success': variant === 'success',
      'tw:bg-error-light tw:text-error': variant === 'error',
    }"
    :style="{ backgroundColor: color }"
  >
    <Icon
      v-if="icon"
      :icon="icon"
      :class="{
        'tw:text-[20px]': size === 'sm',
        'tw:text-[22px]': size === 'md',
        'tw:text-[24px]': size === 'lg',
      }"
    />
    <img
      v-if="src"
      :src="src"
      class="tw:aspect-square"
      :class="{
        'tw:w-[22px]': size === 'sm',
        'tw:w-[34px]': size === 'md',
        'tw:w-[60px]': size === 'lg',
      }"
    />
  </div>
</template>
