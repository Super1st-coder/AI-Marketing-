<script setup lang="ts">
import { useFocusTrap } from "@vueuse/integrations/useFocusTrap";
import { useModalStore } from "@/stores/ModalStore";

const props = withDefaults(
  defineProps<{
    mode?: "fullScreen" | "navbar";
    fallbackFocusToForeground?: boolean;
  }>(),
  {
    mode: "fullScreen",
  },
);

defineOptions({
  inheritAttrs: false,
});

const isOpen = defineModel<boolean>({ required: true });
const modalStore = useModalStore();
const modalId = ref(Symbol("modal"));

const outerParent = ref<HTMLDivElement>();
const innerParent = ref<HTMLDivElement>();

const overlayZIndex = computed(() => modalStore.getZIndex(modalId.value));

const resetScroll = () => {
  if (outerParent.value) {
    resetElementScroll(outerParent.value);
  }
};

defineExpose({
  element: computed(() => outerParent.value),
  resetScroll,
});

const { activate, deactivate, hasFocus } = useFocusTrap(outerParent, {
  preventScroll: true,
  escapeDeactivates: false,
  initialFocus: false,
  allowOutsideClick: true,
  clickOutsideDeactivates: false,
  fallbackFocus: props.fallbackFocusToForeground
    ? () => innerParent.value!
    : undefined,
});

// Handle modal store locking/unlocking, also uses immediate option
// to ensure to lock the modal when the component is mounted
watch(
  isOpen,
  (value) => {
    if (value) {
      modalStore.lock(modalId.value);
    } else {
      modalStore.unlock(modalId.value);
    }
  },
  { immediate: true },
);

// Handle focus trap activation when outerParent becomes available
watch(
  isOpen,
  async (isOpen) => {
    if (isOpen) {
      await nextTick();

      if (!hasFocus.value) {
        activate();
      }
    } else {
      if (hasFocus.value) {
        deactivate();
      }
    }
  },
  { immediate: true },
);

// Cleanup on unmount - handle case where modal is still open when component unmounts
onBeforeUnmount(() => {
  if (isOpen.value) {
    // Unlock modal
    modalStore.unlock(modalId.value);

    // Cleanup focus trap
    if (hasFocus.value) {
      deactivate();
    }
  }
});
</script>

<template>
  <Teleport to="#modals">
    <div
      ref="outerParent"
      v-show="isOpen"
      class="tw:fixed tw:left-0 tw:w-full tw:overflow-y-scroll"
      :class="{
        'tw:hidden': !isOpen,

        'tw:top-0 tw:h-full': mode === 'fullScreen',
        'tw:top-[66px] tw:h-[calc(100vh-66px)]': mode === 'navbar',
      }"
      :style="{ zIndex: overlayZIndex }"
    >
      <div
        ref="innerParent"
        class="tw:h-full tw:min-h-full tw:w-full"
        tabindex="-1"
        v-bind="$attrs"
      >
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<style>
.block-scroll {
  position: fixed;
  top: var(--body-scroll-y);
  width: 100%;
  height: 100%;
}
</style>
