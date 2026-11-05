<script lang="ts" setup>
import { computed, useSlots } from "vue";
import { RouteLocationRaw, RouterLink } from "vue-router";

export interface ButtonProps {
  variant?: CommonComponentVariant;
  color?: CommonComponentColor;
  size?: CommonComponentSize;
  disabled?: boolean;
  icon?: string;
  leftIcon?: string;
  external?: boolean;
  to?: RouteLocationRaw;
  replace?: boolean;
  as?: string;
  isLoading?: boolean;
  customColor?: string;
  square?: boolean;
  type?: "submit" | "button" | "reset";
  shadow?: boolean;
  uppercase?: boolean;

  keepTextVariantPadding?: boolean;
  disableScaleAnimation?: boolean;
}

const props = withDefaults(defineProps<ButtonProps>(), {
  color: "primary",
  variant: "solid",
  size: "lg",
  as: "button",
  external: false,
  shadow: true,
  uppercase: false,
});
const slots = useSlots();

const isIconButton = computed(
  () => (props.icon || props.leftIcon) && !slots.default,
);
const isSquare = computed(() => isIconButton.value || props.square);
const isDisabled = computed(() => props.isLoading || props.disabled);

const { className, style } = useCommonComponentClasses({
  color: () => props.color,
  variant: () => props.variant,
  customColor: () => props.customColor,
  hoverable: true,
  disabled: () => isDisabled.value,
});

const iconClass = computed(() => [
  "tw:inline-block tw:shrink-0 tw:relative",
  {
    "tw:text-[20px]": props.size !== "2xl",
    "tw:text-[24px]": props.size === "2xl",
    "tw:invisible": props.isLoading,
  },
]);

const useFlex = computed(() => props.icon || props.leftIcon || props.to);
const component = computed(() =>
  props.external ? "a" : props.to ? RouterLink : props.as,
);
</script>

<template>
  <component
    :is="component"
    :target="external ? '_blank' : undefined"
    :replace="replace"
    class="tw:relative"
    :type="as === 'button' && props.type ? props.type : undefined"
    :class="[
      className,
      // Rounded
      'tw:rounded-lg',
      {
        'tw:uppercase': uppercase,
        'tw:transition-transform tw:active:scale-[98%]':
          !isDisabled && !disableScaleAnimation,

        // No pointer events for links and router links when disabled
        'tw:pointer-events-none':
          (component === RouterLink || component === 'a') && disabled,

        // Flex
        'tw:flex tw:items-center tw:justify-center': useFlex,
        'tw:gap-2': useFlex && size !== '2xl',
        'tw:gap-3': useFlex && size === '2xl',

        // Text
        'tw:text-center': !isIconButton,
        'tw:font-medium': !isIconButton,
        'tw:leading-[18px]':
          !isIconButton && (props.size === 'xs' || props.size === 'sm'),
        'tw:leading-[22px]': !isIconButton && props.size === 'md',
        'tw:leading-[24px]': !isIconButton && props.size === 'lg',
        'tw:text-[13px]': !isIconButton && size === 'xs',
        'tw:text-sm': !isIconButton && (size === 'sm' || size === 'md'),
        'tw:text-base': !isIconButton && (size === 'lg' || size === 'xl'),
        'tw:text-lg': !isIconButton && size === '2xl',

        // Paddings
        'tw:px-2.5 tw:py-1.5': !isSquare && size === 'xs',
        'tw:px-3.5 tw:py-2': !isSquare && size === 'sm',
        'tw:px-4 tw:py-2.5': !isSquare && size === 'md',
        'tw:px-[18px] tw:py-2.5': !isSquare && size === 'lg',
        'tw:px-5 tw:py-3': !isSquare && size === 'xl',
        'tw:px-7 tw:py-4': !isSquare && size === '2xl',
        'tw:px-0!': !isSquare && variant === 'text' && !keepTextVariantPadding,

        // Square button
        'tw:aspect-square tw:shrink-0': isSquare,
        'tw:w-[30px]': isSquare && size === 'xs',
        'tw:w-[36px]': isSquare && size === 'sm',
        'tw:w-[40px]': isSquare && size === 'md',
        'tw:w-[44px]': isSquare && size === 'lg',
        'tw:w-[48px]': isSquare && size === 'xl',
        'tw:w-[56px]': isSquare && size === '2xl',

        // Shadow
        'tw:shadow-[0_1px_2px] tw:shadow-[#101828]/5':
          shadow && variant !== 'text',
      },
    ]"
    :style="style"
    :disabled="isDisabled"
    :to="to"
  >
    <slot name="before" />

    <Icon v-if="leftIcon" :icon="leftIcon" :class="iconClass" />

    <span v-if="$slots.default" :class="{ 'tw:invisible': isLoading }">
      <slot />
    </span>

    <Icon v-if="icon" :icon="icon" :class="iconClass" />

    <span
      v-if="isLoading"
      class="tw:absolute tw:top-1/2 tw:left-1/2 tw:flex tw:-translate-x-1/2 tw:-translate-y-1/2"
    >
      <CircleLoader />
    </span>

    <slot name="after" />
  </component>
</template>
