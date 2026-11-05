<script setup lang="ts">
import {
  autoUpdate,
  flip,
  offset,
  Placement,
  shift,
  size as constrainSize,
  useFloating,
} from "@floating-ui/vue";

interface Props {
  icon: string;
  size?: Extract<CommonComponentSize, "sm" | "md" | "lg">;
  placement?: Placement | undefined;
  /** When true, the floating panel has no padding. */
  noContentPadding?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  placement: "bottom-end",
  size: "sm",
  noContentPadding: false,
});

const emit = defineEmits(["close"]);

defineOptions({ inheritAttrs: false });

const reference = ref<HTMLElement>();
const floating = ref<HTMLElement>();
const { floatingStyles } = useFloating(reference, floating, {
  placement: () => props.placement,
  transform: false,
  whileElementsMounted: autoUpdate,
  middleware: [
    offset(4),
    flip(),
    shift(),
    constrainSize({
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
  <button
    ref="reference"
    @click="isOpen = !isOpen"
    type="button"
    v-bind="$attrs"
    :class="{
      'tw:text-xl': size === 'sm',
      'tw:text-2xl': size === 'md',
      'tw:text-[32px]': size === 'lg',
    }"
  >
    <Icon :icon="icon" />
  </button>

  <Teleport to="#dropdowns">
    <div
      v-if="isOpen"
      ref="floating"
      :style="floatingStyles"
      class="tw:z-1000 tw:flex tw:flex-col tw:overflow-y-auto tw:rounded-xl tw:bg-white tw:shadow-[0_4px_30px_#3D29221F]"
      :class="{ 'tw:p-3': !noContentPadding }"
    >
      <slot name="options" />
    </div>
  </Teleport>
</template>
