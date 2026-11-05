// Base z-index for modal overlays; each new modal gets base + stack index.
export const MODAL_BASE_Z_INDEX = 30;

/**
 * Store to manage body scroll locking and z-index stacking for modals.
 * Uses an array of Symbols to track individual modal instances.
 */
export const useModalStore = defineStore("ModalStore", () => {
  const openModals = ref<symbol[]>([]);
  const savedScrollTop = ref(0);

  watch(
    () => openModals.value.length,
    (length, previousLength) => {
      if (previousLength === 0 && length > 0) {
        // First modal opening - save scroll position and lock
        savedScrollTop.value = document.documentElement.scrollTop;
        document.documentElement.style.setProperty(
          "--body-scroll-y",
          `-${savedScrollTop.value}px`,
        );
        document.documentElement.classList.add("block-scroll");
      } else if (previousLength > 0 && length === 0) {
        // Last modal closing - unlock body scroll
        document.documentElement.classList.remove("block-scroll");
        document.documentElement.scrollTop = savedScrollTop.value;
      }
    },
  );

  const lock = (modalId: symbol) => {
    if (openModals.value.includes(modalId)) return;
    openModals.value.push(modalId);
  };

  const unlock = (modalId: symbol) => {
    const index = openModals.value.indexOf(modalId);
    if (index !== -1) {
      openModals.value.splice(index, 1);
    }
  };

  // Index for a modal by id (by position in stack)
  const getIndex = (modalId: symbol) => openModals.value.indexOf(modalId);

  // Z-index for a modal by id (by position in stack)
  const getZIndex = (modalId: symbol) => {
    const index = getIndex(modalId);
    return index === -1 ? 0 : MODAL_BASE_Z_INDEX + index;
  };

  return {
    openModals: readonly(openModals),
    modalCount: computed(() => openModals.value.length),
    getIndex,
    getZIndex,
    lock,
    unlock,
  };
});
