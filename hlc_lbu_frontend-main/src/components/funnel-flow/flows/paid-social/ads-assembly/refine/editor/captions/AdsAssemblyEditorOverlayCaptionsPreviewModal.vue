<script setup lang="ts">
import { getPinnedOrNearestFourFiveFormatIndex } from "@/services/funnel-flow/paid-social/AdsApi";

const isOpen = defineModel<boolean>({ required: true });

const store = useFunnelPaidSocialAdsAssemblyStore();

// Video ads show their video instead of the banner formats, so they have no
// formats to move through or edit in Abyssale
const isVideo = computed(() => store.isCurrentSetVideoFormat);
const { src: videoSrc, refresh: refreshVideoSrc } = useStoredFileSrc(() => {
  const video = store.getCurrentAdVariantVideo(store.currentVariant?.id);
  return { storage_key: video?.storage_key, storage_url: video?.storage_path };
});

const formats = computed(() => store.currentVariant?.media.formats ?? []);
const attributes = computed(
  () => store.currentVariant?.channel_attributes ?? [],
);

function getAttributePayload(attributeName: string) {
  return attributes.value.find((attribute) => attribute.name === attributeName);
}

const primaryTextAttribute = computed(() =>
  getAttributePayload("primary_text"),
);
const primaryText = ref<string>(
  primaryTextAttribute.value?.payloads[0]?.payload ?? "",
);

const headlineAttribute = computed(() => getAttributePayload("headline"));
const headline = ref<string>(
  headlineAttribute.value?.payloads[0]?.payload ?? "",
);

const descriptionAttribute = computed(() => getAttributePayload("description"));
const description = ref<string>(
  descriptionAttribute.value?.payloads[0]?.payload ?? "",
);

const ctaAttribute = computed(() => getAttributePayload("cta"));
const cta = ref<string>(ctaAttribute.value?.payloads[0]?.payload ?? "");

const { currentItem: currentFormat, move } = useSliderRef(
  formats,
  getPinnedOrNearestFourFiveFormatIndex(formats.value),
);
</script>

<template>
  <Modal
    v-model="isOpen"
    closeButton
    alignment="top"
    :maxWidth="900"
    scrollable="inner"
    v-slot="{ close }"
  >
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.ads.refine.editor.preview-ads-title") }}

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.preview-ads-description",
          )
        }}
      </template>
    </ModalHeader>

    <ModalBody :paddings="false">
      <div class="tw:flex tw:flex-col tw:items-start tw:lg:flex-row">
        <div
          class="tw:sticky tw:top-0 tw:flex tw:grow tw:flex-col tw:gap-8 tw:p-8"
        >
          <AdsAssemblyEditorOverlayCaptionsPreviewModalField
            v-if="primaryTextAttribute"
            :attribute="primaryTextAttribute"
            v-model="primaryText"
          />

          <AdsAssemblyEditorOverlayCaptionsPreviewModalField
            v-if="headlineAttribute"
            :attribute="headlineAttribute"
            v-model="headline"
          />

          <AdsAssemblyEditorOverlayCaptionsPreviewModalField
            v-if="descriptionAttribute"
            :attribute="descriptionAttribute"
            v-model="description"
          />

          <AdsAssemblyEditorOverlayCaptionsPreviewModalField
            v-if="ctaAttribute"
            :attribute="ctaAttribute"
            v-model="cta"
          />
        </div>

        <div class="tw:grow tw:bg-gray-100 tw:p-8 tw:lg:max-w-[394px]">
          <AdPreview
            size="lg"
            :primaryText="primaryText"
            :headline="headline"
            :description="description"
            :cta="cta"
            :imageSrc="currentFormat?.visual_url ?? currentFormat?.preview_url"
            :videoSrc="videoSrc"
            aspectRatio="auto"
            @videoError="refreshVideoSrc"
          />

          <div
            v-if="!isVideo"
            class="tw:mt-5 tw:flex tw:grow tw:justify-center tw:gap-4"
          >
            <button type="button" @click="move(-1)" class="tw:text-2xl">
              <Icon icon="tabler-chevron-left" />
            </button>

            <button type="button" @click="move(1)" class="tw:text-2xl">
              <Icon icon="tabler-chevron-right" />
            </button>
          </div>

          <Button
            v-if="!isVideo"
            leftIcon="tabler:edit"
            color="secondary"
            variant="outlined"
            class="tw:mt-4"
            type="button"
            external
            :href="`https://app.abyssale.com/designs/${store.currentVariant?.media.template_id}/visual/${currentFormat?.visual_id}`"
          >
            Edit in Abyssale
          </Button>
        </div>
      </div>
    </ModalBody>

    <ModalFooter>
      <Button color="primary" variant="label" type="button" @click="close">
        {{
          $t("funnel-flow.paid-social.ads.refine.editor.continue-editing-ad")
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
