import type { ImageLibraryFile } from "@/stores/ImageLibraryStore";

export function useImageLibraryModal(options?: {
  id?: string;
  disabled?: MaybeRefOrGetter<boolean>;
  onSelect?: (file: ImageLibraryFile) => void | Promise<void>;
}) {
  const isOpen = ref(false);
  const store = useImageLibraryStore();
  const targetId = ref(Symbol(options?.id ?? "ImageLibraryModal"));

  watch(
    () => store.selectedFile,
    async (file) => {
      if (!file) return;
      if (store.lastTarget !== targetId.value) return;

      await options?.onSelect?.(file);
      isOpen.value = false;
    },
  );

  function open() {
    if (toValue(options?.disabled)) return;
    store.setActiveTarget(targetId.value);
    isOpen.value = true;
  }

  return { isOpen, open };
}
