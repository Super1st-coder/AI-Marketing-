import VideoApi from "@/services/funnel-flow/paid-social/VideoApi";

/** A file the video flow stores: a video, an audio or an image. */
export type StoredFile = {
  /** Permanent reference to the stored file. */
  storage_key?: string | null;
  /** The saved link to it, which expires within the hour. */
  storage_url?: string | null;
};

/**
 * A link that fails sooner than this after it was made hasn't expired: the
 * file is missing or can't be shown. Asking for another one would loop.
 */
const REFRESH_COOLDOWN_MS = 60 * 1000;

/**
 * A link to show or play a stored file. The saved links expire within the
 * hour, so it gets a fresh one from the storage key. Files without a storage
 * key were never stored, so their saved link is used.
 *
 * The link is requested again when the key or the saved link changes. A video
 * assembled again is stored with the same key but saved with a new link, so it
 * gets a new one too. Otherwise the old link would keep playing the cached old
 * file.
 *
 * A link already in use can expire too, for example in a tab left open. Call
 * `refresh` from the `error` event of the element that shows the file to get
 * a new one. A timer wouldn't do: browsers slow them down in background tabs
 * and stop them while the computer sleeps.
 */
export function useStoredFileSrc(
  file: MaybeRefOrGetter<StoredFile | null | undefined>,
) {
  const storageKey = computed(() => toValue(file)?.storage_key);
  const storageUrl = computed(() => toValue(file)?.storage_url ?? undefined);

  const refreshCount = ref(0);
  let requestedAt = 0;

  const src = ref<string>();

  watch(
    [storageKey, storageUrl, refreshCount],
    async ([key, savedUrl], _previous, onCleanup) => {
      // A newer request replaces this one, so its answer is ignored
      let isStale = false;
      onCleanup(() => {
        isStale = true;
      });

      if (!key) {
        src.value = savedUrl;
        return;
      }

      requestedAt = Date.now();
      try {
        const { url } = await VideoApi.getDownloadUrl(key);
        if (!isStale) src.value = url;
      } catch (error) {
        console.error("Failed to get the stored file download URL:", error);
        // What shows the file is still useful without it
        if (!isStale) src.value = undefined;
      }
    },
    { immediate: true },
  );

  /** Gets a new link, for when the current one stopped working. */
  function refresh() {
    if (!storageKey.value) return;
    if (Date.now() - requestedAt < REFRESH_COOLDOWN_MS) return;

    // Also set here, so elements failing together ask only once
    requestedAt = Date.now();
    refreshCount.value++;
  }

  return { src, refresh };
}
