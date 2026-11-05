export default function useCopyElementToClipboard(
  element: MaybeRefOrGetter<HTMLElement | undefined>,
) {
  const isCopying = ref(false);

  const copy = async () => {
    isCopying.value = true;

    try {
      await nextTick();

      const el = toValue(element);
      if (!el) {
        throw new Error("Element not found");
      }

      await copyElement(el);
    } catch (error) {
      console.error("Failed to copy to clipboard:", error);
    } finally {
      isCopying.value = false;
    }
  };

  function copyElement(target) {
    // Create and set range
    const range = document.createRange();
    range.setStart(target, 0);
    range.setEnd(target, 1);

    // Deselect
    window.getSelection()?.removeAllRanges();

    // Select the range
    window.getSelection()?.addRange(range);

    // Copy
    document.execCommand("copy");

    // Deselect
    window.getSelection()?.removeAllRanges();
  }

  return { copy, isCopying };
}
