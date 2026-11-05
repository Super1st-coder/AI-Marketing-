<script lang="ts" setup>
interface Props {
  variant?: "primary" | "secondary";
  size?: "lg" | "sm";
  padding?: boolean;
}

withDefaults(defineProps<Props>(), {
  variant: "primary",
  size: "lg",
  padding: true,
});

const store = useMenusStore();
</script>

<template>
  <h2
    class="tw:text-balance"
    :class="{
      'tw:px-3': padding && store.isMenuVisuallyExpanded,

      'tw:font-bold': variant === 'primary',
      'tw:font-semibold tw:text-gray-500': variant === 'secondary',

      'tw:text-sm': size === 'sm',
      'tw:text-base': size === 'lg',
    }"
  >
    <slot v-if="store.isMenuVisuallyExpanded" />
    <wbr v-else />
  </h2>
</template>
