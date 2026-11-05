<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import AdsApi, {
  AdMediaBanner,
  getPinnedFormat,
} from "@/services/funnel-flow/paid-social/AdsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, object, string } from "yup";
import useGenerateAbyssaleVisuals from "../composables/useGenerateAbyssaleVisuals";

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();
const { generateVisuals, isWaitingForAbyssale } = useGenerateAbyssaleVisuals();

const generatePreviews = ref(false);
const isPreviewOpen = ref(false);

const imagePromises = store.currentVariant?.media.images_banner?.map(
  async (banner) => {
    if (!store.currentAd || !store.currentChannel) {
      throw new UnidentifiedError();
    }

    const response = await AdsApi.getMediaImage(
      store.brandId,
      store.campaignId,
      store.currentAd.ad_id,
      store.currentChannel.channel_id,
      store.currentVariant!.id,
      banner.name,
    );

    return {
      name: banner.name,
      image: response ?? banner.preview_url,
    };
  },
);

const initialImages = imagePromises
  ? (await Promise.all(imagePromises))
      .filter((image) => image !== undefined)
      // Sort by name
      .sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { numeric: true }),
      )
  : [];

const schema = computed(() =>
  toTypedSchema(
    object({
      images: array()
        .of(
          object({
            name: string().required(t("forms.required-field")),
            image: mixed<ImageLibraryFile | string | Blob>(),
          }),
        )
        .required(t("forms.required-field")),
      pinned_format: string().required(
        t("funnel-flow.paid-social.ads.refine.editor.pin-format-required"),
      ),
    }),
  ),
);

const {
  handleSubmit,
  isSubmitting,
  values,
  meta,
  submitSuccess,
  isFieldDirty,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    images: initialImages,
    pinned_format: getPinnedFormat(store.currentVariant?.media.formats)?.id,
  },
  validateOnMount: true,
  resetDirtyOnSubmit: true,
});

// Read banners from the store (refetched after each save) instead of the form,
// so fields like `image_id` stay up to date.
const bannersByName = computed(
  () =>
    new Map<string, AdMediaBanner>(
      store.currentVariant?.media.images_banner?.map((banner) => [
        banner.name,
        banner,
      ]) ?? [],
    ),
);

async function save() {
  assert(store.currentAd, "Current ad is not set");
  assert(store.currentChannel, "Current channel is not set");
  assert(store.currentVariant, "Current variant is not set");

  const { currentAd, currentChannel, currentVariant } = store;

  const images = values.images ?? [];

  // Upload one image at a time, concurrent uploads overwrite each other in the back-end
  for (let index = 0; index < images.length; index++) {
    const { image, name } = images[index];

    // Ignore if the image is not dirty
    if (!isFieldDirty(`images.${index}.image`)) {
      continue;
    }

    if (image instanceof Blob) {
      if ("lastModified" in image) {
        // It's a file

        if (image.raw) {
          await AdsApi.uploadMediaImage({
            brand_id: store.brandId,
            campaign_id: store.campaignId,
            ad_id: store.currentAd!.ad_id,
            channel_id: currentChannel.channel_id,
            variant_id: currentVariant.id,
            image_name: name,
            image: image,
          });
        } else {
          await AdsApi.uploadMediaImageFromImgLibrary({
            brand_id: store.brandId,
            campaign_id: store.campaignId,
            ad_id: currentAd.ad_id,
            channel_id: currentChannel.channel_id,
            variant_id: currentVariant.id,
            image_name: name,
            image_id: image.libraryId,
          });
        }
      }

      // Otherwise it's a blob, the initial one downloaded from the back-end,
      // so there's nothing to upload
    }
  }

  if (values.pinned_format) {
    await AdsApi.pinAdVariantFormat({
      brand_id: store.brandId,
      campaign_id: store.campaignId,
      ad_id: currentAd.ad_id,
      channel_id: currentChannel.channel_id,
      variant_id: currentVariant.id,
      format_id: values.pinned_format,
    });
  }

  // Refetch the ad
  await store.refetchCurrentAd();
}

const onSubmit = handleSubmit(async (_values) => {
  await save();

  if (generatePreviews.value) {
    // Generate visuals in abyssale
    const success = await generateVisuals();

    if (!success) {
      return;
    }

    // Display modal with results
    isPreviewOpen.value = true;
    generatePreviews.value = false;
  }
});

async function handleSaveAndExit() {
  await save();
}
</script>

<template>
  <!-- The content grows, so the footer stays at the bottom of the screen -->
  <form class="tw:flex tw:grow tw:flex-col" @submit.prevent="onSubmit">
    <Container :maxWidth="1088" class="tw:grow tw:py-8">
      <div class="tw:flex tw:flex-col tw:items-start tw:gap-16 tw:lg:flex-row">
        <div class="tw:grid tw:grow tw:grid-cols-1 tw:gap-6">
          <AdsAssemblyEditorOverlayAbyssaleAlerts />

          <div
            class="tw:grid tw:grid-cols-1 tw:gap-4 tw:sm:grid-cols-2 tw:lg:grid-cols-3"
          >
            <template v-for="(image, index) in values.images" :key="image.name">
              <AdsAssemblyEditorOverlayBannerMediaField
                v-if="bannersByName.get(image.name)"
                :index="index"
                :banner="bannersByName.get(image.name)!"
              />
            </template>
          </div>
        </div>

        <AdsAssemblyEditorOverlayPreviewTemplate
          @openPreview="isPreviewOpen = true"
        />
      </div>
    </Container>

    <AdsAssemblyEditorOverlayFooter>
      <Button variant="label" :uppercase="false" :isLoading="isSubmitting">
        {{ $t("funnel-flow.paid-social.ads.refine.editor.save-changes") }}
      </Button>

      <Button
        :uppercase="false"
        :isLoading="isSubmitting || isWaitingForAbyssale"
        @click="generatePreviews = true"
      >
        {{
          $t("funnel-flow.paid-social.ads.refine.editor.save-generate-preview")
        }}
      </Button>
    </AdsAssemblyEditorOverlayFooter>

    <!-- Save locking -->
    <ModalFormSaveOrDiscard
      :isDirty="meta.dirty && !submitSuccess"
      :saveFn="handleSaveAndExit"
    >
      <template #description>
        {{ $t("funnel-flow.paid-social.ads.refine.editor.pending-changes") }}
      </template>
    </ModalFormSaveOrDiscard>

    <AdFormatsPreviewModal
      v-if="store.currentSet && store.currentAd && store.currentVariant"
      v-model="isPreviewOpen"
      :adSetName="store.currentSet.name"
      :adName="store.currentAd.ad_name"
      :formats="store.currentVariant.media.formats ?? []"
    />
  </form>
</template>
