import { MaybeRef } from "vue";

export function useMaxHeight(
  selectors: MaybeRef<string[]>,
  enabled: MaybeRef<boolean> | undefined = true,
) {
  const maxHeight = ref(0);
  const { width, height } = useWindowSize();

  const recalculateHeight = () => {
    unref(selectors).forEach((selector) => {
      // Get all the elements using the selector
      const elements = document.querySelectorAll<HTMLElement>(unref(selector));

      // Remove the previously assigned height
      elements.forEach((element) => {
        element.style.height = "auto";
      });

      if (unref(enabled)) {
        // Determine the max height of the elements
        maxHeight.value = Number.MIN_SAFE_INTEGER;
        elements.forEach((element) => {
          const elementHeight = element.scrollHeight;
          if (elementHeight > maxHeight.value) {
            maxHeight.value = elementHeight;
          }
        });

        // Apply the max height
        elements.forEach((element) => {
          element.style.height = `${maxHeight.value}px`;
        });
      }
    });
  };

  // Recalculate on mounted and update
  onMounted(recalculateHeight);
  onUpdated(recalculateHeight);

  // Recalculate when the window size changes
  watch(width, recalculateHeight);
  watch(height, recalculateHeight);

  // Recalculate if enabled changes
  if (isRef(enabled)) {
    watch(enabled, recalculateHeight);
  }

  return { recalculateHeight };
}
