<script lang="ts" setup>
import {
  autoUpdate,
  flip,
  offset,
  Placement,
  shift,
  size,
  useFloating,
} from "@floating-ui/vue";
import { ButtonProps } from "./Button.vue";

interface Props extends ButtonProps {
  placement?: Placement | undefined;
  /** When true, the floating panel has no padding. */
  noContentPadding?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  placement: "bottom-end",
  noContentPadding: false,
});

const emit = defineEmits(["close"]);

defineOptions({
  inheritAttrs: false,
});

const buttonProps = computed(() => {
  // Exclude local props
  const { placement, noContentPadding, ...restOfProperties } = props;
  return restOfProperties;
});

const reference = ref<HTMLElement>();
const floating = ref<HTMLElement>();
const { floatingStyles } = useFloating(reference, floating, {
  placement: () => props.placement,
  whileElementsMounted: autoUpdate,
  middleware: [
    offset(4),
    flip(),
    shift(),
    size({
      padding: 8,
      apply({ availableHeight, elements }) {
        Object.assign(elements.floating.style, {
          maxHeight: `${availableHeight}px`,
        });
      },
    }),
  ],
});

const isOpen = ref(false);

const close = () => {
  isOpen.value = false;
};

onClickOutside(floating, () => {
  if (isOpen.value) {
    close();
  }
});

function closeDropdown() {
  isOpen.value = false;
  emit("close");
}

provide("closeDropdown", closeDropdown);
</script>

<template>
  <Button
    v-if="$slots.default"
    ref="reference"
    @click="isOpen = !isOpen"
    v-bind="{ ...buttonProps, ...$attrs, disableScaleAnimation: true }"
  >
    <slot />
  </Button>
  <Button
    v-else
    ref="reference"
    @click="isOpen = !isOpen"
    v-bind="{ ...buttonProps, ...$attrs, disableScaleAnimation: true }"
  />

  <Teleport to="#dropdowns">
    <div
      v-if="isOpen"
      ref="floating"
      :style="floatingStyles"
      class="tw:z-1000 tw:flex tw:flex-col tw:overflow-y-auto tw:rounded-xl tw:bg-white tw:shadow-[0_4px_30px_#3D29221F]"
      :class="{ 'tw:p-3': !noContentPadding }"
    >
      <slot name="options" :close="close" />
    </div>
  </Teleport>
</template>
