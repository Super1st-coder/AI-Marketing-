<script lang="ts" setup>
import {
  autoUpdate,
  flip,
  MaybeElement,
  offset,
  Placement,
  ReferenceElement,
  shift,
  useFloating,
} from "@floating-ui/vue";

defineOptions({
  inheritAttrs: false,
});

export interface DropdownBaseProps {
  target: MaybeElement<ReferenceElement | undefined>;
  placement?: Placement | undefined;
  maxWidth?: string | number;
  variant?: "dark" | "light" | "error";
}

const props = withDefaults(defineProps<DropdownBaseProps>(), {
  placement: "bottom",
  variant: "dark",
});

const floating = ref<HTMLElement>();
const target = computed(() => props.target);

const { floatingStyles } = useFloating(target, floating, {
  placement: () => props.placement,
  whileElementsMounted: autoUpdate,
  middleware: [offset(4), flip(), shift()],
});
</script>

<template>
  <Teleport to="#dropdowns">
    <div
      ref="floating"
      :style="{
        ...floatingStyles,
        maxWidth: typeof maxWidth === 'number' ? `${maxWidth}px` : maxWidth,
      }"
      class="tw:z-1000 tw:rounded-2xl"
      :class="{
        'tw:bg-gray-600/90 tw:text-white tw:backdrop-blur-xs':
          variant === 'dark',
        'tw:border tw:border-gray-300 tw:bg-white tw:shadow-[0_8px_24px] tw:shadow-gray-900/8':
          variant === 'light',
        'tw:bg-error-500/90 tw:text-white tw:backdrop-blur-xs':
          variant === 'error',
      }"
      v-bind="$attrs"
    >
      <slot />
    </div>
  </Teleport>
</template>
