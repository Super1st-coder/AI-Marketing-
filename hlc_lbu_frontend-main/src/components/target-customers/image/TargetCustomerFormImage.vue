<script lang="ts" setup>
import {
  ImageStudioGeneratedImage,
  ImageStudioGenerateFnOptions,
  ImageStudioSelectedMainImage,
  ImageStudioVariationImage,
} from "@/components/images/studio/types";
import { TargetCustomerFormData } from "../TargetCustomerForm.vue";
import ProductsApi, { ProductData } from "@/services/ProductsApi";
import BuyerPersonImagesApi, {
  BuyerPersonMainImage,
} from "@/services/BuyerPersonImagesApi";
import { UnidentifiedError } from "@/services/common-errors.ts";

const { data, goBack } = useMultiStepFormContext<TargetCustomerFormData>();
const brandId = useBrandId();
const { t } = useI18n();
const isLocked = computed(() => data.value.locked);

const variationLoaderSteps = computed(() => [
  t("buyer-person.image.variations-loader.steps.studying-features"),
  t("buyer-person.image.variations-loader.steps.keeping-face-shape"),
  t("buyer-person.image.variations-loader.steps.creating-angles"),
  t("buyer-person.image.variations-loader.steps.finalizing-options"),
]);

// Fetch all products of the brand
const allProducts = ref<ProductData[]>(
  await fetchAllItems((range) =>
    ProductsApi.getList(brandId, {
      range,
      order: { updatedAt: "desc" },
    }),
  ),
);

const isGenerateModalOpen = ref(false);
const isEditorOverlayOpen = ref(false);
const isStudioHelpVideoOpen = ref(false);
const studioImages = ref<ImageStudioGeneratedImage[]>([]);
const selectedMainImage = ref<ImageStudioSelectedMainImage | undefined>(
  undefined,
);

const variationGenerationErrorMessage = ref<string | undefined>(undefined);
const isVariationsLoaderOpen = ref(false);
const isSelectingVariants = ref(false);
const variationImages = ref<ImageStudioVariationImage[]>([]);
const areVariationsReady = ref(false);
const currentScreen = ref<"selection" | "variations">("selection");
const isExploreLibraryOpen = ref(false);
const isEditorContentLoading = ref(false);

function toStudioImages(
  main_images: BuyerPersonMainImage[],
  previous: ImageStudioGeneratedImage[] = [],
): ImageStudioGeneratedImage[] {
  return main_images.map(
    ({ id, image_id, image_url, prompt, has_variants, selected }) => {
      const previousImage = previous.find((image) => image.id === id);

      // Format expected by the image studio
      return {
        id,
        image_id,
        image_url,
        prompt,
        has_variants,
        selected,
        fetchBlob: true,
        image_blob: previousImage?.image_blob,
      };
    },
  );
}

async function getMainImages() {
  // Update list of main images
  const { main_images } = (
    await BuyerPersonImagesApi.getMainImageList(
      data.value.brandId,
      data.value.id,
    )
  ).data;

  return main_images;
}

async function refreshStudioImages(options?: { showEditorLoader?: boolean }) {
  if (options?.showEditorLoader) {
    isEditorContentLoading.value = true;
  }

  try {
    const mainImages = await getMainImages();
    studioImages.value = toStudioImages(mainImages, studioImages.value);
    return mainImages;
  } finally {
    if (options?.showEditorLoader) {
      isEditorContentLoading.value = false;
    }
  }
}

const mainImages = await refreshStudioImages();
const selected = mainImages.find((image) => image.selected);

// Prefetch selected main image and open the variations screen
if (selected) {
  const { variants } = (
    await BuyerPersonImagesApi.getMainImageVariants(
      data.value.brandId,
      data.value.id,
      selected.image_id,
    )
  ).data;

  selectedMainImage.value = {
    image_url: selected.image_url,
    prompt: selected.prompt,
    image_id: selected.image_id,
  };
  variationImages.value = variants.map(
    ({ id, image_id, image_url, prompt, label }) => ({
      id,
      image_id,
      label,
      image_url,
      prompt,
    }),
  );
  currentScreen.value = "variations";
}

const hasMainImages = computed(() => studioImages.value.length > 0);

function handleResumeProgress() {
  if (selectedMainImage.value) {
    currentScreen.value = "variations";
  } else if (hasMainImages.value) {
    isEditorOverlayOpen.value = true;
  }
}

async function handleSuccessAutomaticModeGeneration() {
  if (isLocked.value) {
    return;
  }

  isGenerateModalOpen.value = false;
  isEditorOverlayOpen.value = true;
  await refreshStudioImages({ showEditorLoader: true });
}

async function handleSelectManualMode() {
  if (isLocked.value) {
    return;
  }

  isGenerateModalOpen.value = false;
  isEditorOverlayOpen.value = true;
  await refreshStudioImages({ showEditorLoader: true });
}

async function handleGenerateMainImage({
  prompt,
  variations,
  mode,
  targetImage,
  photographyEffect,
  targetProduct,
  referenceImages,
  visualStyle,
}: ImageStudioGenerateFnOptions): Promise<ImageStudioGeneratedImage[]> {
  if (isLocked.value) {
    return [];
  }

  // Call the endpoint to generate the main image
  const response = await BuyerPersonImagesApi.startEditMainImageJob({
    brand_id: brandId,
    bperson_id: data.value.id,
    custom_prompt: prompt ?? "",
    n_variants: variations,
    // normal / moreLikeThis → no base image; edit → image being edited
    base_image_id: mode === "edit" ? targetImage?.image_id : undefined,
    photography_effect: photographyEffect?.name,
    product_id: targetProduct?.id,
    reference_images: referenceImages,
    visual_style: visualStyle?.name,
  });

  // Wait for the job to finish
  const jobId = response.data.job_id;
  const result = await pooling(
    async () => {
      const { data: response } =
        await BuyerPersonImagesApi.getGenerateMainImageListJobResult(jobId);

      return response;
    },
    (response) => response.status === "DONE" || response.status === "FAILED",
    TARGET_CUSTOMER_IMAGE_JOB_POLLING_INTERVAL_MS,
    { timeoutMs: TARGET_CUSTOMER_IMAGE_JOB_TIMEOUT_MS },
  );

  // Check if the job failed
  if (result.status === "FAILED") {
    // generalErrorMessage.value = result.error;
    throw new UnidentifiedError();
  }

  // Snapshot existing IDs so we can return only newly generated images
  const existingIds = new Set(studioImages.value.map((image) => image.id));
  const main_images = await getMainImages();

  // Return only the newly generated images
  const newImages = main_images
    .filter((image) => !existingIds.has(image.id))
    .map<ImageStudioGeneratedImage>(({ id, image_id, image_url, prompt }) => ({
      id,
      image_id,
      image_url,
      fetchBlob: true,
      prompt,
      has_variants: false,
    }));

  if (newImages.length === 0) {
    throw new UnidentifiedError();
  }

  return newImages;
}

async function handleDeleteMainImage(image: ImageStudioGeneratedImage) {
  if (isLocked.value) {
    return;
  }

  // Call delete endpoint
  await BuyerPersonImagesApi.deleteMainImage({
    brand_id: brandId,
    bperson_id: data.value.id,
    main_image_id: image.id,
  });
}

async function handleSelectGeneratedImage(image: ImageStudioGeneratedImage) {
  assert(image.image_blob);

  if (isLocked.value && !image.has_variants) {
    return;
  }

  if (image.has_variants) {
    try {
      isSelectingVariants.value = true;
      variationGenerationErrorMessage.value = undefined;

      const { variants } = (
        await BuyerPersonImagesApi.getMainImageVariants(
          data.value.brandId,
          data.value.id,
          image.image_id,
        )
      ).data;

      // Set new state
      selectedMainImage.value = {
        image_blob: image.image_blob,
        image_url: image.image_url,
        prompt: image.prompt,
        image_id: image.image_id,
      };
      variationImages.value = variants.map(
        ({ id, image_id, image_url, prompt, label }) => ({
          id,
          image_id,
          label,
          image_url,
          prompt,
        }),
      );

      // Close editor and open the variations screen
      isEditorOverlayOpen.value = false;
      currentScreen.value = "variations";
    } catch (error) {
      console.log(error);
      variationGenerationErrorMessage.value = t("global.unexpected-error");
    } finally {
      isSelectingVariants.value = false;
    }
  } else {
    try {
      // Open the loader
      isVariationsLoaderOpen.value = true;
      variationGenerationErrorMessage.value = undefined;

      // Start the variants generation job
      const response = await BuyerPersonImagesApi.startGenerateVariantsJob({
        brand_id: data.value.brandId,
        bperson_id: data.value.id,
        image_id: image.image_id,
      });

      // Wait for the job to finish
      const jobId = response.data.job_id;
      const result = await pooling(
        async () => {
          const { data: response } =
            await BuyerPersonImagesApi.getGenerateMainImageListJobResult(jobId);

          return response;
        },
        (response) =>
          response.status === "DONE" || response.status === "FAILED",
        TARGET_CUSTOMER_IMAGE_JOB_POLLING_INTERVAL_MS,
        { timeoutMs: TARGET_CUSTOMER_IMAGE_JOB_TIMEOUT_MS },
      );

      // Check if the job failed
      if (result.status === "FAILED") {
        throw new UnidentifiedError();
      }

      // Fetch the generated variants
      const { variants } = (
        await BuyerPersonImagesApi.getMainImageVariants(
          data.value.brandId,
          data.value.id,
          image.image_id,
        )
      ).data;

      // Do not open the overlay unless variants were actually generated
      if (variants.length === 0) {
        throw new UnidentifiedError();
      }

      // Mark this main image as having variants so the label shows when going back
      studioImages.value = studioImages.value.map((mainImage) =>
        mainImage.image_id === image.image_id
          ? { ...mainImage, has_variants: true }
          : mainImage,
      );

      // Display the last step in loader for a moment
      areVariationsReady.value = true;
      await sleep(4 * SECOND_IN_MS);

      // Set new state
      selectedMainImage.value = {
        image_blob: image.image_blob,
        image_url: image.image_url,
        prompt: image.prompt,
        image_id: image.image_id,
      };
      variationImages.value = variants.map(
        ({ id, image_id, image_url, prompt, label }) => ({
          id,
          image_id,
          label,
          image_url,
          prompt,
        }),
      );

      // Close editor and open the variations screen
      isEditorOverlayOpen.value = false;
      currentScreen.value = "variations";
    } catch (error) {
      console.log(error);
      variationGenerationErrorMessage.value = t("global.unexpected-error");
    } finally {
      areVariationsReady.value = false;
      isVariationsLoaderOpen.value = false;
    }
  }
}

function handleUnselectMainImage() {
  variationGenerationErrorMessage.value = undefined;
}

async function handleVariationsGoBack() {
  currentScreen.value = "selection";
  isEditorOverlayOpen.value = true;
  await refreshStudioImages({ showEditorLoader: true });
}

async function handleUploadFileSuccess(
  selectedFile: ImageLibraryFile,
  variants: ImageStudioVariationImage[],
  mainImage: BuyerPersonMainImage,
) {
  if (isLocked.value) {
    return;
  }

  await refreshStudioImages();
  isExploreLibraryOpen.value = false;
  selectedMainImage.value = { ...mainImage, image_blob: selectedFile };
  variationImages.value = variants;
  currentScreen.value = "variations";
}
</script>

<template>
  <FormStepLayout v-if="currentScreen === 'selection'" :maxWidth="910">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=Kqw5Y6v0SoM"
    >
      {{ $t("buyer-person.image.heading") }}

      <template #description>
        {{ $t("buyer-person.image.description") }}
      </template>
    </PageTitle>

    <CardGrid :columns="3">
      <SuggestionCard v-if="hasMainImages" icon="tabler:user-circle">
        <template #title>
          {{ $t("buyer-person.image.resume-progress.title") }}
        </template>

        <template #description>
          {{ $t("buyer-person.image.resume-progress.description") }}
        </template>

        <template #link>
          <Link
            is="button"
            type="button"
            icon="tabler-arrow-narrow-right"
            @click="handleResumeProgress"
          >
            {{ $t("buyer-person.image.resume-progress.action") }}
          </Link>
        </template>
      </SuggestionCard>

      <SuggestionCard v-if="!isLocked" icon="custom:hi-luca">
        <template #title>
          {{ $t("buyer-person.image.generate-with-ai.title") }}
        </template>

        <template #description>
          {{ $t("buyer-person.image.generate-with-ai.description") }}
        </template>

        <template #link>
          <Link
            is="button"
            type="button"
            icon="tabler-arrow-narrow-right"
            @click="isGenerateModalOpen = true"
          >
            {{ $t("buyer-person.image.generate-with-ai.action") }}
          </Link>
        </template>
      </SuggestionCard>

      <SuggestionCard v-if="!isLocked" icon="tabler:copy">
        <template #title>
          {{ $t("buyer-person.image.explore-library.title") }}
        </template>

        <template #description>
          {{ $t("buyer-person.image.explore-library.description") }}
        </template>

        <template #link>
          <Link
            is="button"
            type="button"
            icon="tabler-arrow-narrow-right"
            @click="isExploreLibraryOpen = true"
          >
            {{ $t("buyer-person.image.explore-library.action") }}
          </Link>
        </template>
      </SuggestionCard>
    </CardGrid>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
      </WizardCardActions>
    </template>

    <!-- Modal to select the image generation method-->
    <TargetCustomerFormImageModalGenerate
      v-if="isGenerateModalOpen"
      v-model="isGenerateModalOpen"
      :products="allProducts"
      @successAutomaticMode="handleSuccessAutomaticModeGeneration"
      @selectManualMode="handleSelectManualMode"
    />

    <!-- Image studio overlay -->
    <ImageStudioOverlay
      v-if="isEditorOverlayOpen"
      v-model="isEditorOverlayOpen"
      v-model:images="studioImages"
      :brandId="brandId"
      enableProductAttachment
      enableEditing
      enableMoreLikeThis
      enableAddReference
      enableVariations
      enablePhotographicEffects
      enableStyle
      enableImproveResultsModal
      :deleteFn="handleDeleteMainImage"
      :generateFn="handleGenerateMainImage"
      :isContentLoading="isEditorContentLoading"
      :readOnly="isLocked"
      :selectButtonProps="{
        leftIcon: isLocked ? undefined : 'custom:hi-luca',
        isLoading: isSelectingVariants,
      }"
      @select="handleSelectGeneratedImage"
      @unselect="handleUnselectMainImage"
    >
      <template #headerTitle>
        {{ $t("buyer-person.image.studio.header-title") }}
      </template>

      <template #headerSubtitle>
        {{ data.name }}
      </template>

      <template #title>
        {{ $t("buyer-person.image.studio.title") }}
      </template>

      <template #description>
        <i18n-t
          keypath="buyer-person.image.studio.description"
          tag="span"
          class="tw:whitespace-pre-line"
        >
          <template #watchVideo>
            <Link is="button" underline @click="isStudioHelpVideoOpen = true">
              {{ $t("buyer-person.image.watch-video") }}
            </Link>
          </template>
        </i18n-t>
      </template>

      <template #selectLabel="{ image }">
        {{
          image.has_variants
            ? $t("buyer-person.image.studio.view-variants")
            : $t("buyer-person.image.studio.select-label")
        }}
      </template>

      <template #selectionTitle>
        {{ $t("buyer-person.image.studio.selection-title") }}
      </template>

      <template #selectionDescription>
        {{ $t("buyer-person.image.studio.selection-description") }}
      </template>

      <template #selectionAlert>
        <Alert v-if="variationGenerationErrorMessage" type="error" autoScroll>
          {{ variationGenerationErrorMessage }}
        </Alert>
      </template>

      <template #galleryDescription>
        {{ $t("buyer-person.image.studio.gallery-description") }}
      </template>
    </ImageStudioOverlay>

    <!-- Image studio help video -->
    <ModalVideoPlayer
      v-if="isStudioHelpVideoOpen"
      v-model="isStudioHelpVideoOpen"
      :src="TARGET_CUSTOMER_IMAGE_STUDIO_HELP_VIDEO_URL"
    >
      <template #title>{{ $t("image-studio.video-modal.title") }}</template>
    </ModalVideoPlayer>

    <!-- Ring loader -->
    <ModalRingLoader
      v-if="isVariationsLoaderOpen"
      v-model="isVariationsLoaderOpen"
      :isReady="areVariationsReady"
      :interval="TARGET_CUSTOMER_IMAGE_RING_LOADER_INTERVAL_MS"
      :steps="variationLoaderSteps"
    >
      <template #title>
        {{ $t("buyer-person.image.variations-loader.title") }}
      </template>
      <template #description>
        {{ $t("buyer-person.image.variations-loader.description") }}
      </template>
    </ModalRingLoader>

    <!-- Modal to upload image from library -->
    <TargetCustomerFormImageModalExploreLibrary
      v-if="isExploreLibraryOpen"
      v-model="isExploreLibraryOpen"
      @success="handleUploadFileSuccess"
    />
  </FormStepLayout>

  <TargetCustomerFormImageVariations
    v-else-if="currentScreen === 'variations' && selectedMainImage"
    :mainImage="selectedMainImage"
    :initialImages="variationImages"
    @goBack="handleVariationsGoBack"
  />
</template>
