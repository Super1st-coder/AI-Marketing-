export type ImageFetcher = (
  signal: AbortSignal,
) => Promise<Blob | undefined | null> | null | undefined;

export default function useFetchImage(
  fetcher: ImageFetcher,
  { delay = 0 }: { delay?: number } = {},
) {
  const isLoading = ref(false);
  const isError = ref(false);
  const imageBlob = ref<Blob | undefined>();

  const src = useObjectUrl(imageBlob);
  const abortController = ref<AbortController>(new AbortController());

  const ready = useTimeout(delay);

  onMounted(() => {
    if (delay > 0) {
      isLoading.value = true;
    }
  });

  const refetch = async () => {
    isLoading.value = true;
    isError.value = false;

    try {
      const image = await fetcher(abortController.value.signal);

      if (image) {
        imageBlob.value = image;
      }
    } catch (error) {
      console.error(error);
      imageBlob.value = undefined;
      isError.value = true;
    } finally {
      isLoading.value = false;
    }
  };

  watch(ready, async () => {
    await refetch();
  });

  onUnmounted(() => {
    abortController.value.abort();
  });

  return { isLoading, isError, src, refetch };
}
