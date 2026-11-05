<script setup lang="ts">
import Overlay, { OverlayProps } from "@/components/modals/base/Overlay.vue";
import { modalScrollableInjectionKey } from "@/components/modals/base/useModalContext";

defineOptions({
  inheritAttrs: false,
});

export interface ModalProps extends OverlayProps {
  closeButton?: boolean;
  innerClass?: string;
  alignment?: "center" | "top";
  as?: string;
  maxWidth?: string | number;
  height?: string | number;
  radius?: string | number;
  useCustomClose?: boolean;
  closeOnClickOutside?: boolean;
  overlayClass?: string;
}

const props = withDefaults(defineProps<ModalProps>(), {
  alignment: "center",
  as: "div",
  closeOnClickOutside: true,
  radius: 24,
});

const emit = defineEmits<{
  customClose: [];
}>();

const isOpen = defineModel<boolean>({ required: true });

const handleClose = () => {
  if (props.useCustomClose) {
    emit("customClose");
  } else {
    isOpen.value = false;
  }
};

const overlayRef = ref<InstanceType<typeof Overlay>>();
const overlayElement = computed(() => overlayRef.value?.element);

const handleClickOutside = () => {
  if (props.closeOnClickOutside) {
    handleClose();
  }
};

const resetScroll = () => {
  overlayRef.value?.resetScroll();
};

watch(isOpen, (value) => {
  if (!value) {
    resetScroll();
  }
});

defineExpose({
  overlayElement: overlayElement,
  resetScroll,
});

provide(
  modalScrollableInjectionKey,
  computed(() => props.scrollable ?? "outer"),
);
</script>

<template>
  <Overlay
    :fallbackFocusToForeground="fallbackFocusToForeground"
    ref="overlayRef"
    v-model="isOpen"
    class="tw:flex tw:items-start tw:justify-center tw:p-2 tw:sm:p-5"
    :class="props.overlayClass"
    :scrollable="scrollable"
    @click="handleClickOutside"
  >
    <component
      :is="as"
      class="tw:relative tw:w-full tw:bg-white"
      :class="[
        innerClass,
        {
          'tw:m-auto': alignment === 'center',
          'tw:flex tw:max-h-full tw:flex-col tw:overflow-hidden':
            scrollable === 'inner',
        },
      ]"
      :style="{
        maxWidth: typeof maxWidth === 'number' ? `${maxWidth}px` : maxWidth,
        height: typeof height === 'number' ? `${height}px` : height,
        borderRadius:
          typeof radius === 'number' ? `${radius}px` : radius || undefined,
      }"
      v-bind="$attrs"
    >
      <ModalCloseButton
        v-if="closeButton"
        class="tw:absolute tw:top-0 tw:right-0"
        @click="handleClose"
      />

      <slot v-bind="{ close: handleClose }" />
    </component>
  </Overlay>
</template>
