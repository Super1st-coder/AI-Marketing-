import { UnidentifiedError } from "@/services/common-errors";
import AdsApi, {
  isVisualGenerationPending,
} from "@/services/funnel-flow/paid-social/AdsApi";
import type { InjectionKey, Ref } from "vue";

export const abyssaleGenerationErrorKey: InjectionKey<Ref<string | undefined>> =
  Symbol("abyssaleGenerationError");

export default function useGenerateAbyssaleVisuals() {
  const { t } = useI18n();
  const store = useFunnelPaidSocialAdsAssemblyStore();
  const generalErrorMessage = ref<string | undefined>(undefined);

  provide(abyssaleGenerationErrorKey, generalErrorMessage);

  // Create abort controller
  const poolAbortController = ref(new AbortController());

  // Abort pooling when unmounting
  onUnmounted(() => {
    poolAbortController.value.abort();
  });

  const isWaitingForAbyssale = computed(() => {
    if (!store.currentVariant) {
      return false;
    }

    return isVisualGenerationPending(store.currentVariant.media);
  });

  async function generateVisuals() {
    try {
      generalErrorMessage.value = undefined;

      if (
        !store.currentAd ||
        !store.currentChannel ||
        !store.currentVariant ||
        !store.currentVariant.media.elements
      ) {
        throw new UnidentifiedError();
      }

      // Generate visuals in abyssale
      await AdsApi.generateAbyssaleMediaVisuals(
        store.brandId,
        store.campaignId,
        store.currentAd.ad_id,
        store.currentChannel.channel_id,
        store.currentVariant.id,
        {
          elements: store.currentVariant.media.elements,
        },
      );

      // Wait for the generation to be completed
      await pooling(
        async () => {
          // Refetch the whole ad
          await store.refetchCurrentAd();

          if (!store.currentVariant) {
            throw new UnidentifiedError();
          }

          // Return the media data
          return store.currentVariant.media;
        },
        (media) => {
          // Check if the generation is pending based on the media
          // or if the pooling has been aborted
          return (
            !isVisualGenerationPending(media) ||
            poolAbortController.value.signal.aborted === true
          );
        },
        5000,
      );

      // Check if there are errors
      const anyError = store.currentVariant.media.formats?.some(
        (format) => format.errors && format.errors.length > 0,
      );

      if (anyError) {
        return false;
      }

      return true;
    } catch (error: unknown) {
      if (error instanceof Error && error.name === "AbortError") {
        return false;
      }

      generalErrorMessage.value = t(
        "funnel-flow.paid-social.ads.refine.editor.ad-preview-generation-error",
      );
      return false;
    }
  }

  return {
    isWaitingForAbyssale,
    generateVisuals,
    generalErrorMessage,
  };
}
