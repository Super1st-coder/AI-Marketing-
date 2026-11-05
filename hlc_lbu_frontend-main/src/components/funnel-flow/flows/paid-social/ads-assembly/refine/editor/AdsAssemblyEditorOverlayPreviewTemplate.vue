<script setup lang="ts">
import {
  AdMediaFormat,
  getPinnedOrNearestFourFiveFormat,
} from "@/services/funnel-flow/paid-social/AdsApi";

const emit = defineEmits<{ openPreview: [] }>();

const store = useFunnelPaidSocialAdsAssemblyStore();
const formats = computed(() => store.currentVariant?.media.formats ?? []);
const visualId = ref<string | undefined>(
  getPinnedOrNearestFourFiveFormat(formats.value)?.visual_id ?? undefined,
);

function onChangeFormat(format: AdMediaFormat) {
  if (format.visual_id) {
    visualId.value = format.visual_id;
  }
}
</script>

<template>
  <!-- The 9:16 video preview is narrower than the banner -->
  <div
    class="tw:sticky tw:top-[calc(72px+1em)] tw:shrink-0"
    :class="
      store.isCurrentSetVideoFormat ? 'tw:basis-[318px]' : 'tw:basis-[424px]'
    "
  >
    <slot>
      <AbyssaleTemplatePreviewSlider
        :formats="formats"
        @changeFormat="onChangeFormat"
      />
    </slot>

    <!-- Video ads have no banner to preview or edit in Abyssale -->
    <div
      v-if="store.currentVariant && !store.isCurrentSetVideoFormat"
      class="tw:grid tw:grid-cols-2 tw:gap-3"
    >
      <Button
        leftIcon="tabler:eye"
        color="secondary"
        variant="outlined"
        class="tw:mt-4"
        type="button"
        @click="emit('openPreview')"
      >
        {{ $t("funnel-flow.paid-social.ads.refine.editor.banner-preview") }}
      </Button>

      <Tooltip :disabled="!!visualId" placement="top" :maxWidth="280">
        <Button
          leftIcon="tabler:edit"
          color="secondary"
          variant="outlined"
          class="tw:mt-4"
          type="button"
          external
          :disabled="!visualId"
          :href="`https://app.abyssale.com/designs/${store.currentVariant.media.template_id}/visual/${visualId}`"
        >
          Edit in Abyssale
        </Button>

        <template #content>
          {{
            $t(
              "funnel-flow.paid-social.ads.refine.editor.edit-in-abyssale-disabled-tooltip",
            )
          }}
        </template>
      </Tooltip>
    </div>
  </div>
</template>
