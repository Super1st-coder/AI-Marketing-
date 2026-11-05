<script setup lang="ts">
import type { AdPreviewProps } from "@/components/ads/AdPreview.vue";
import LucaGuideAdsApi, {
  parseIframeFromHtml,
  type LucaGuideAd,
} from "@/services/guide/LucaGuideAdsApi";

interface Props extends Pick<AdPreviewProps, "size" | "clampLines"> {
  ad: LucaGuideAd;
  accountName: string;
}

const props = withDefaults(defineProps<Props>(), {
  size: "lg",
  clampLines: false,
});

const isVideo = props.ad.asset_type.toLowerCase() === "video";

type VideoPlayback = {
  videoSrc?: string;
  iframeSrc?: string;
  iframeHeight?: number;
  iframeAllow?: string;
};

async function resolveVideoPlayback(
  adExternalId: string,
): Promise<VideoPlayback> {
  try {
    const source = await LucaGuideAdsApi.getVideoSource(adExternalId);

    if (source.ok && source.source_url) {
      return { videoSrc: source.source_url };
    }

    if (source.ok && source.embed_url) {
      return { iframeSrc: source.embed_url };
    }
  } catch (error) {
    console.error("Failed to load ad video source:", error);
  }

  try {
    const preview = await LucaGuideAdsApi.getPreview(adExternalId);

    if (preview.ok && preview.iframe) {
      const iframe = parseIframeFromHtml(preview.iframe);

      if (iframe) {
        return {
          iframeSrc: iframe.src,
          iframeHeight: iframe.height,
          iframeAllow: iframe.allow,
        };
      }
    }
  } catch (error) {
    console.error("Failed to load ad preview iframe:", error);
  }

  return {};
}

// Ticket 18: for static ads, resolve the creative image FRESH via the proxy (the stored
// image_url is an expired fbcdn link → 403 → broken preview). Fall back to the stored url if the
// proxy can't resolve it, so the preview is never worse than before.
async function resolveImageSrc(): Promise<string | undefined> {
  if (isVideo) {
    return undefined;
  }
  const proxied = await LucaGuideAdsApi.getCreativeImageUrl(
    props.ad.ad_external_id,
  );
  return proxied ?? props.ad.image_url ?? undefined;
}

const [content, playback, resolvedImageSrc] = await Promise.all([
  LucaGuideAdsApi.getContent(props.ad.ad_external_id),
  isVideo
    ? resolveVideoPlayback(props.ad.ad_external_id)
    : Promise.resolve({} as VideoPlayback),
  resolveImageSrc(),
]);

// Release the object URL we minted (blob:) when the panel goes away, to avoid a memory leak.
onBeforeUnmount(() => {
  if (resolvedImageSrc?.startsWith("blob:")) {
    URL.revokeObjectURL(resolvedImageSrc);
  }
});

const primaryText = computed(() => content.primary_text ?? undefined);

const headline = computed(
  () => content.headline ?? props.ad.headline ?? undefined,
);

const description = computed(() => content.description ?? undefined);

const cta = computed(() => content.cta ?? props.ad.cta ?? undefined);

const imageSrc = computed(() => resolvedImageSrc ?? undefined);
</script>

<template>
  <AdPreview
    :accountName="accountName"
    :primaryText="primaryText"
    :headline="headline"
    :description="description"
    :cta="cta"
    :imageSrc="imageSrc"
    :videoSrc="playback.videoSrc"
    :isVideo="isVideo"
    :size="size"
    :clampLines="clampLines"
    aspectRatio="auto"
  >
    <template v-if="playback.iframeSrc" #media>
      <iframe
        :src="playback.iframeSrc"
        :title="$t('meta-ad-preview.video')"
        :height="playback.iframeHeight"
        class="tw:w-full"
        :allow="playback.iframeAllow || 'autoplay; encrypted-media; fullscreen'"
        allowfullscreen
      />
    </template>
  </AdPreview>
</template>
