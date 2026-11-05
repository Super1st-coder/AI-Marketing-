export function useObjectOrStringUrl(
  object: MaybeRefOrGetter<Blob | MediaSource | string | null | undefined>,
): Readonly<Ref<string | undefined, string | undefined>> {
  const source = computed(() => toValue(object));

  const fileUrl = useObjectUrl(() => {
    if (typeof source.value !== "string") {
      return source.value;
    }

    return undefined;
  });

  // Handle both File objects and string URLs
  const finalImageUrl = computed(() => {
    if (!source.value) return undefined;
    if (typeof source.value === "string") return source.value;
    return fileUrl.value;
  });

  return finalImageUrl;
}
