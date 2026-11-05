<script setup lang="ts">
export type CardBaseColor =
  | "default"
  | "primary"
  | "secondary"
  | "success"
  | "error"
  | "warning"
  | "info";

export type CardBaseHoverColor = Exclude<CardBaseColor, "default">;

export type CardBaseOutlineColor = CardBaseColor;

export interface CardBaseProps {
  is?: string | Component;
  color?: CardBaseColor;
  hoverColor?: CardBaseHoverColor;
  outlineColor?: CardBaseOutlineColor;
  disabled?: boolean;
  shadow?: boolean;
  borderless?: boolean;
  borderWidth?: number;
  /** Border radius size: `xs` (8px), `sm` (12px), `md` (16px), `lg` (20px). */
  borderRadius?: "xs" | "sm" | "md" | "lg";
  isLoading?: boolean;
  /** When true, applies the background color at 20% opacity. */
  softBackground?: boolean;
}

const props = withDefaults(defineProps<CardBaseProps>(), {
  is: "div",
  color: "default",
  outlineColor: "default",
  shadow: true,
  borderless: false,
  borderWidth: 1,
  borderRadius: "lg",
  softBackground: false,
});

const element = ref<HTMLElement>();

defineExpose({
  element: computed(() => element.value),
});

const disabled = computed(() => props.disabled || props.isLoading);
</script>

<template>
  <component
    ref="element"
    :is="is"
    :style="{ borderWidth: borderless ? '0px' : `${borderWidth}px` }"
    :class="{
      'tw:relative': isLoading,

      // Border radius
      'tw:rounded-[8px]': borderRadius === 'xs',
      'tw:rounded-[12px]': borderRadius === 'sm',
      'tw:rounded-[16px]': borderRadius === 'md',
      'tw:rounded-[20px]': borderRadius === 'lg',

      // Shadow
      'tw:shadow-[0_2px_12px] tw:shadow-gray-900/3': shadow,

      // Background
      'tw:bg-white': color === 'default',
      'tw:bg-primary-100': color === 'primary' && !softBackground,
      'tw:bg-primary-100/40': color === 'primary' && softBackground,
      'tw:bg-gray-200': color === 'secondary' && !softBackground,
      'tw:bg-gray-200/20': color === 'secondary' && softBackground,
      'tw:bg-success-100': color === 'success' && !softBackground,
      'tw:bg-success-100/40': color === 'success' && softBackground,
      'tw:bg-error-100': color === 'error' && !softBackground,
      'tw:bg-error-100/20': color === 'error' && softBackground,
      'tw:bg-warning-100': color === 'warning' && !softBackground,
      'tw:bg-warning-100/40': color === 'warning' && softBackground,
      'tw:bg-blue-100': color === 'info' && !softBackground,
      'tw:bg-blue-100/40': color === 'info' && softBackground,

      // Hover
      'tw:hover:border-primary tw:hover:bg-primary-100':
        hoverColor === 'primary' && !disabled,
      'tw:hover:border-success tw:hover:bg-success-100':
        hoverColor === 'success' && !disabled,
      'tw:hover:border-error tw:hover:bg-error-100':
        hoverColor === 'error' && !disabled,
      'tw:hover:border-warning tw:hover:bg-warning-100':
        hoverColor === 'warning' && !disabled,
      'tw:hover:border-blue-500 tw:hover:bg-blue-100':
        hoverColor === 'info' && !disabled,

      // Outline
      'tw:border-gray-300': color === 'default' && outlineColor === 'default',
      'tw:border-primary':
        (color === 'primary' && outlineColor === 'default') ||
        outlineColor === 'primary',
      'tw:border-success':
        (color === 'success' && outlineColor === 'default') ||
        outlineColor === 'success',
      'tw:border-error':
        (color === 'error' && outlineColor === 'default') ||
        outlineColor === 'error',
      'tw:border-warning':
        (color === 'warning' && outlineColor === 'default') ||
        outlineColor === 'warning',
      'tw:border-blue':
        (color === 'info' && outlineColor === 'default') ||
        outlineColor === 'info',

      // Disabled
      'tw:cursor-pointer': hoverColor && !disabled,
      'tw:pointer-events-none tw:opacity-60': disabled,

      // Text left when the component is a button
      'tw:text-left': is === 'button',
    }"
    :disabled="disabled"
  >
    <slot />

    <span
      v-if="isLoading"
      class="tw:absolute tw:top-1/2 tw:left-1/2 tw:flex tw:-translate-x-1/2 tw:-translate-y-1/2"
    >
      <CircleLoader class="tw:text-[30px] tw:text-primary" />
    </span>
  </component>
</template>
