<script lang="ts" setup>
export interface ChipProps {
  size?: Extract<CommonComponentSize, "sm" | "md" | "lg">;
  color?: CommonComponentColor;
  variant?: CommonComponentVariant;
  customColor?: string;
  leftIcon?: string;
  icon?: string;
  uppercase?: boolean;
}

const props = withDefaults(defineProps<ChipProps>(), {
  color: "default",
  size: "lg",
  variant: "solid",
  uppercase: false,
});

const { className, style } = useCommonComponentClasses({
  color: () => props.color,
  variant: () => props.variant,
  customColor: () => props.customColor,
});
</script>

<template>
  <p
    class="tw:inline-flex tw:items-center tw:gap-0.5 tw:rounded-lg tw:leading-tight tw:font-medium"
    :class="[
      className,
      {
        'tw:px-2 tw:py-[3px] tw:text-xs': size === 'md' || size === 'sm',
        'tw:px-2.5 tw:py-1 tw:text-sm': size === 'lg',
        'tw:uppercase': uppercase,
      },
    ]"
    :style="style"
  >
    <Icon v-if="leftIcon" :icon="leftIcon" class="tw:text-base" />
    <slot />
    <Icon v-if="icon" :icon="icon" class="tw:text-base" />
  </p>
</template>
