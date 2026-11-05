import { ShallowRef } from "vue";

export default function useSliderRef<T>(
  items: MaybeRefOrGetter<T[]>,
  initialIndex?: MaybeRefOrGetter<number | undefined>,
  options: {
    refs?: Readonly<ShallowRef<Element[] | null, Element[] | null>>;
  } = { refs: undefined },
) {
  const currentIndex = ref<number | undefined>(toValue(initialIndex));

  const move = (direction: number) => {
    if (currentIndex.value === undefined) {
      return;
    }

    const _items = toValue(items);
    let targetIndex = currentIndex.value + direction;
    if (targetIndex > _items.length - 1) targetIndex = 0;
    if (targetIndex < 0) targetIndex = _items.length - 1;
    currentIndex.value = targetIndex;
  };

  const currentItem = computed(() => {
    const _items = toValue(items);
    return currentIndex.value !== undefined
      ? _items[currentIndex.value]
      : undefined;
  });

  // Scroll to selected item on mount
  watch(currentIndex, async (newIndex) => {
    if (options.refs && newIndex !== undefined) {
      const targetElement = options.refs.value?.[newIndex];

      if (targetElement) {
        targetElement.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "center",
        });
      }
    }
  });

  return {
    items: computed(() => toValue(items)),
    currentIndex,
    currentItem,
    move,
  };
}
