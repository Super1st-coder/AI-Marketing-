<script setup lang="ts">
import {
  ImageStudioGeneratedImage,
  ImageStudioGenerateError,
  ImageStudioGenerateFnOptions,
} from "@/components/images/studio/types";
import { useImageLibraryModal } from "@/composables/useImageLibraryModal";
import {
  ADS_ASSEMBLY_ENABLE_GENERATE_AI_IMAGE_SOURCE,
  ADS_ASSEMBLY_EDIT_MEDIA_IMAGE_JOB_POLLING_INTERVAL_MS,
  ADS_ASSEMBLY_EDIT_MEDIA_IMAGE_JOB_TIMEOUT_MS,
} from "@/constants/funnel-flow/paid-social";
import { UnidentifiedError } from "@/services/common-errors";
import UtilsApi from "@/services/UtilsApi";
import AdsApi, {
  AdMediaBanner,
} from "@/services/funnel-flow/paid-social/AdsApi";

const props = defineProps<{ index: number; banner: AdMediaBanner }>();

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();

const name = computed(() => `images.${props.index}.image`);
const label = computed(() => anyCaseToText(props.banner.name));

const { value, setValue, meta } = useField<
  ImageLibraryFile | Blob | string | undefined
>(() => name.value);

// The edit endpoint only accepts the image saved on the banner. A replaced
// image isn't linked to the banner (and has no `image_id`) until it's saved.
const isEditWithAIDisabled = computed(() => meta.dirty);

const imageSrc = useObjectOrStringUrl(value);

const { isOpen: isModalOpen, open: openLibrary } = useImageLibraryModal({
  id: "AdsAssemblyEditorOverlayBannerMediaField",
  onSelect: (file) => setValue(file, true),
});

const customSources = computed(() =>
  ADS_ASSEMBLY_ENABLE_GENERATE_AI_IMAGE_SOURCE
    ? [
        {
          slug: "generate",
          label: t(
            "funnel-flow.paid-social.ads.refine.editor.banner.generate-ai-image",
          ),
          icon: "custom:hi-luca",
          color: "primary" as const,
          cropper: true,
        },
      ]
    : [],
);

const isEditorOverlayOpen = ref(false);
const createdStudioImages = ref<ImageStudioGeneratedImage[]>([]);
const isSelectingVariants = ref(false);
const variationGenerationErrorMessage = ref<string | undefined>(undefined);

async function handleEditImageWithAI() {
  isEditorOverlayOpen.value = true;
}

async function handleGenerateImage(
  options: ImageStudioGenerateFnOptions,
): Promise<ImageStudioGeneratedImage[]> {
  if (!store.currentAd || !store.currentChannel || !store.currentVariant) {
    throw new UnidentifiedError();
  }

  const baseImageId = props.banner.image_id;

  if (!baseImageId) {
    throw new UnidentifiedError();
  }

  let jobId: string;

  try {
    const response = await AdsApi.startEditMediaImageJob({
      brand_id: store.brandId,
      campaign_id: store.campaignId,
      ad_id: store.currentAd.ad_id,
      channel_id: store.currentChannel.channel_id,
      variant_id: store.currentVariant.id,
      image_name: props.banner.name,
      image_id: baseImageId,
      n_variations: options.variations,
      custom_prompt: options.prompt ?? null,
      expand_zoom_option: options.expandZoom ?? null,
    });

    jobId = response.data.job_id;
  } catch (error: any) {
    console.error("Failed to start the edit image job:", error);

    await sleep(500);

    // The back-end needs a prompt, an expand / zoom option or both
    if (
      error?.message?.code === "SYSVAL001" &&
      error?.message?.text?.includes("expand_zoom_option")
    ) {
      throw new ImageStudioGenerateError(
        t(
          "funnel-flow.paid-social.ads.refine.editor.banner.studio.prompt-or-expand-zoom-required",
        ),
      );
    }

    throw error;
  }

  const result = await pooling(
    async () => {
      const { data: jobResult } =
        await AdsApi.getEditMediaImageJobResult(jobId);

      return jobResult;
    },
    (jobResult) => jobResult.status === "DONE" || jobResult.status === "FAILED",
    ADS_ASSEMBLY_EDIT_MEDIA_IMAGE_JOB_POLLING_INTERVAL_MS,
    { timeoutMs: ADS_ASSEMBLY_EDIT_MEDIA_IMAGE_JOB_TIMEOUT_MS },
  );

  if (result.status !== "DONE") {
    throw new UnidentifiedError();
  }

  // The studio needs numeric IDs, the library ID is kept in `image_id`
  const idBase = Date.now();

  return result.result.variations.map<ImageStudioGeneratedImage>(
    (variation, index) => ({
      id: idBase + index,
      image_id: variation.id,
      image_url: variation.url,
      fetchBlob: true,
      prompt: variation.prompt,
    }),
  );
}

async function handleSelectGeneratedImage(image: ImageStudioGeneratedImage) {
  try {
    isSelectingVariants.value = true;
    variationGenerationErrorMessage.value = undefined;

    // The generated image is already in the library, so we store it as a
    // library file. On save, this makes the parent link it to the banner
    // using its library ID.
    const blob =
      image.image_blob ??
      (await UtilsApi.getBinaryFromPresignedUrl(image.image_url));

    const file: ImageLibraryFile = Object.assign(
      new File([blob], props.banner.name, { type: blob.type }),
      {
        raw: false as const,
        libraryId: image.image_id,
        librarySource: "image-library" as const,
      },
    );

    setValue(file, true);

    // Close editor
    isEditorOverlayOpen.value = false;
  } catch (error) {
    console.error("Failed to select generated image:", error);
    variationGenerationErrorMessage.value = t("global.unexpected-error");
  } finally {
    isSelectingVariants.value = false;
  }
}

function handleUnselectImage() {
  variationGenerationErrorMessage.value = undefined;
}
</script>

<template>
  <div
    class="tw:group tw:relative tw:aspect-square tw:overflow-hidden tw:rounded-2xl tw:border tw:border-gray-300 tw:bg-gray-500"
  >
    <ImgFile
      :src="imageSrc"
      class="transition cursor-pointer tw:size-full tw:object-contain tw:select-none"
    />

    <!-- Black overlay -->
    <div
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:bg-black/50 tw:opacity-0 tw:transition tw:group-hover:opacity-100"
    ></div>

    <!-- Label -->
    <div class="tw:pointer-events-none tw:absolute tw:inset-0 tw:p-2.5">
      <div class="tw:flex">
        <div
          class="tw:rounded-full tw:bg-gray-100 tw:px-2 tw:py-[3px] tw:text-xs tw:font-medium"
        >
          {{ label }}
        </div>
      </div>
    </div>

    <!-- Actions that are visible on mouse hover -->
    <div
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:opacity-0 tw:transition tw:group-hover:opacity-100"
    >
      <div class="tw:flex tw:h-full tw:items-center tw:justify-center tw:gap-4">
        <!-- Change image button -->
        <Tooltip placement="top" :maxWidth="231">
          <Button
            class="tw:pointer-events-auto"
            size="sm"
            variant="label"
            color="primary"
            type="button"
            icon="tabler:refresh"
            @click="openLibrary"
          />

          <template #content>
            {{
              $t(
                "funnel-flow.paid-social.ads.refine.editor.banner.change-image",
              )
            }}
          </template>
        </Tooltip>

        <!-- Edit image with IA button -->
        <Tooltip placement="top" :maxWidth="231">
          <Button
            class="tw:pointer-events-auto"
            size="sm"
            variant="outlined"
            color="secondary"
            type="button"
            icon="tabler:pencil"
            :disabled="isEditWithAIDisabled"
            @click="handleEditImageWithAI"
          />

          <template #content>
            {{
              isEditWithAIDisabled
                ? $t(
                    "funnel-flow.paid-social.ads.refine.editor.banner.save-before-editing-with-ai",
                  )
                : $t(
                    "funnel-flow.paid-social.ads.refine.editor.banner.edit-image-with-ai",
                  )
            }}
          </template>
        </Tooltip>
      </div>
    </div>

    <!-- Image library modal -->
    <ImageLibraryModal
      v-if="isModalOpen"
      v-model="isModalOpen"
      cropper
      :customSources="customSources"
    >
      <template #source:generate>
        <AdsAssemblyEditorOverlayBannerMediaLibraryGenerate
          :index="index"
          :bannerName="banner.name"
        />
      </template>
    </ImageLibraryModal>

    <!-- Image studio overlay -->
    <ImageStudioOverlay
      v-if="isEditorOverlayOpen"
      v-model="isEditorOverlayOpen"
      v-model:images="createdStudioImages"
      enableVariations
      enableExpandZoom
      allowEmptyPrompt
      :referenceImage="imageSrc"
      :generateFn="handleGenerateImage"
      :selectButtonProps="{
        isLoading: isSelectingVariants,
      }"
      @select="handleSelectGeneratedImage"
      @unselect="handleUnselectImage"
    >
      <template #headerTitle>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.banner.edit-image-with-ai",
          )
        }}
      </template>

      <template #headerSubtitle>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.banner.studio.header-subtitle",
            { id: label },
          )
        }}
      </template>

      <template #selectLabel>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.banner.studio.select-label",
          )
        }}
      </template>

      <template #selectionTitle>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.banner.studio.selection-title",
          )
        }}
      </template>

      <template #selectionDescription>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.banner.studio.selection-description",
          )
        }}
      </template>

      <template #selectionAlert>
        <Alert v-if="variationGenerationErrorMessage" type="error" autoScroll>
          {{ variationGenerationErrorMessage }}
        </Alert>
      </template>

      <template #galleryDescription>
        {{
          $t(
            "funnel-flow.paid-social.ads.refine.editor.banner.studio.gallery-description",
          )
        }}
      </template>
    </ImageStudioOverlay>
  </div>
</template>
