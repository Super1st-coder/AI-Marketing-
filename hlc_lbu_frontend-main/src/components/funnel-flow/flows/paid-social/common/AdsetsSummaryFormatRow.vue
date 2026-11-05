<script setup lang="ts">
import {
  AdByCampaignDefinitionData,
  AdChannelDefinition,
  getChannelSelectedVariant,
  getPinnedOrNearestFourFiveImageFromFormats,
} from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{
  ad: AdByCampaignDefinitionData;
  channel: AdChannelDefinition;
}>();

const selectedVariant = computed(() =>
  getChannelSelectedVariant(props.channel),
);
</script>

<template>
  <div
    v-if="selectedVariant?.media.formats"
    v-bind:key="channel.channel_id"
    class="tw:flex tw:items-start tw:gap-2.5 tw:py-[18px] tw:text-sm"
    :class="{
      'tw:cursor-pointer': selectedVariant.media.formats.length > 0,
    }"
  >
    <span class="tw:grow"> {{ ad.ad_name }} - {{ channel.channel_name }} </span>

    <span class="tw:wrap-normal tw:text-secondary">
      {{
        $t("funnel-flow.paid-social.summary.sets.ads.media-formats-count", {
          count: selectedVariant.media.formats?.length,
        })
      }}
    </span>

    <ImgAndPdf
      :src="
        getPinnedOrNearestFourFiveImageFromFormats(
          selectedVariant.media.formats,
        )
      "
      class="tw:aspect-4/5 tw:w-6 tw:shrink-0 tw:rounded tw:object-cover"
    />
  </div>
</template>
