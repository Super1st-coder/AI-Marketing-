<script setup lang="ts">
import {
  AdByCampaignDefinitionData,
  AdVariant,
  isVisualGenerationPending,
} from "@/services/funnel-flow/paid-social/AdsApi";
import CardBase from "@/components/cards/base/CardBase.vue";
import { VideoDraftAssembledVideo } from "@/services/funnel-flow/paid-social/VideoApi";

defineOptions({
  inheritAttrs: false,
});

const props = defineProps<{
  selected?: boolean;
  hasError?: boolean;
  ad: AdByCampaignDefinitionData;
  adVariant: AdVariant;
  /** Hides the image-only actions: creative direction and deleting. */
  isVideo?: boolean;
  /** The finished video of the variant, shown instead of the banner. Video flow only. */
  video?: VideoDraftAssembledVideo;
}>();

const emit = defineEmits<{
  select: [AdVariant];
  delete: [];
  edit: [AdVariant];
  creativeDirection: [AdVariant];
}>();

const { src: videoSrc, refresh: refreshVideoSrc } = useStoredFileSrc(() => ({
  storage_key: props.video?.storage_key,
  storage_url: props.video?.storage_path,
}));

const isWaitingForAbyssale = computed(
  () => !props.isVideo && isVisualGenerationPending(props.adVariant.media),
);

const selectedVariantId = computed({
  get: () => (props.selected ? props.adVariant.id : undefined),
  set: () => {
    emit("select", props.adVariant);
  },
});

function handleEditVariant() {
  emit("edit", props.adVariant);
}

function handleClick(e: MouseEvent) {
  const target = e.target as HTMLElement;

  // Skip click if the user clicked on a button inside the card (e.g., edit, delete)
  if (target.closest("button")) {
    return;
  }

  emit("select", props.adVariant);
}
</script>

<template>
  <CardBase
    v-if="isWaitingForAbyssale"
    v-bind="$attrs"
    color="secondary"
    class="tw:flex tw:items-center tw:justify-center"
  >
    <CircleLoaderDefault />
  </CardBase>
  <CardBase
    v-else
    ref="cardRef"
    v-bind="$attrs"
    class="tw:flex tw:cursor-pointer tw:flex-col tw:gap-2.5 tw:p-3"
    :outlineColor="selected ? 'primary' : hasError ? 'error' : undefined"
    :borderWidth="2"
    @click="handleClick"
  >
    <FieldBaseRadio
      :name="`variant-${adVariant.id}`"
      :value="adVariant.id"
      v-model="selectedVariantId"
      :label="$t('funnel-flow.paid-social.ads.refine.select-this-variation')"
    />

    <AdPreviewFromData
      :shadow="false"
      clampLines
      class="tw:cursor-pointer"
      :media="adVariant.media"
      :channel_attributes="adVariant.channel_attributes"
      :videoSrc="videoSrc"
      :aspectRatio="isVideo ? 9 / 16 : undefined"
      @videoError="refreshVideoSrc"
    />

    <!-- Creative direction and deleting are image only for now -->
    <div class="tw:flex tw:items-center tw:justify-between tw:gap-1">
      <Button
        v-if="!isVideo"
        icon="custom:hi-luca"
        size="sm"
        variant="label"
        color="primary"
        type="button"
        @click="emit('creativeDirection', adVariant)"
      />

      <!-- TODO: Implement bookmark functionality -->
      <!-- <Button
        icon="tabler:bookmark"
        size="sm"
        variant="text"
        color="secondary"
        type="button"
      /> -->

      <div class="tw:grow"></div>

      <Button
        size="sm"
        color="secondary"
        variant="outlined"
        type="button"
        :uppercase="false"
        @click="handleEditVariant"
      >
        {{ $t("funnel-flow.paid-social.ads.refine.edit-details") }}
      </Button>

      <Button
        v-if="!isVideo"
        icon="tabler:trash"
        size="sm"
        variant="text"
        color="secondary"
        type="button"
        @click="emit('delete')"
      />
    </div>
  </CardBase>
</template>
