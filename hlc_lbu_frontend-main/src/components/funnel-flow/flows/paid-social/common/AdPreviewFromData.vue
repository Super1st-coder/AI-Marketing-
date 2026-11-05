<script setup lang="ts">
import {
  AdChannelAttribute,
  AdMediaDefinition,
  getPinnedOrNearestFourFiveImageFromFormats,
} from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{
  media: Pick<AdMediaDefinition, "formats">;
  channel_attributes: AdChannelAttribute[] | null;
  /** Shown instead of the image when set. */
  videoSrc?: string;
}>();

const emit = defineEmits<{
  /** The video couldn't be loaded or played, e.g. its link expired. */
  videoError: [];
}>();

const { t } = useI18n();

const getAttributePayload = (
  attributeName: string,
  defaultValue: string,
): string => {
  return (
    props.channel_attributes?.find(
      (attribute) => attribute.name === attributeName,
    )?.payloads[0]?.payload ?? defaultValue
  );
};

const primaryText = computed(() =>
  getAttributePayload(
    "primary_text",
    t("funnel-flow.paid-social.ads.channel-attributes.primary_text.label"),
  ),
);

const headline = computed(() =>
  getAttributePayload(
    "headline",
    t("funnel-flow.paid-social.ads.channel-attributes.headline.label"),
  ),
);

const description = computed(() =>
  getAttributePayload(
    "description",
    t("funnel-flow.paid-social.ads.channel-attributes.description.label"),
  ),
);

const cta = computed(() =>
  getAttributePayload(
    "cta",
    t("funnel-flow.paid-social.ads.channel-attributes.cta.label"),
  ),
);

const previewSrc = computed(() =>
  getPinnedOrNearestFourFiveImageFromFormats(props.media.formats),
);
</script>

<template>
  <AdPreview
    :primaryText="primaryText"
    :headline="headline"
    :description="description"
    :cta="cta"
    :imageSrc="previewSrc"
    :videoSrc="videoSrc"
    @videoError="emit('videoError')"
  >
    <template v-if="$slots.media" #media>
      <slot name="media" />
    </template>
  </AdPreview>
</template>
