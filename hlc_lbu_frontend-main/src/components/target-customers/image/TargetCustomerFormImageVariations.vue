<script setup lang="ts">
import {
  ImageStudioGeneratedImage,
  ImageStudioGenerateFnOptions,
  ImageStudioSelectedMainImage,
  ImageStudioVariationImage,
} from "@/components/images/studio/types";
import { TargetCustomerFormData } from "../TargetCustomerForm.vue";
import { UnidentifiedError } from "@/services/common-errors.ts";
import BuyerPersonImagesApi, {
  BuyerPersonMainImageVariant,
} from "@/services/BuyerPersonImagesApi";

const props = defineProps<{
  mainImage: ImageStudioSelectedMainImage;
  initialImages?: ImageStudioVariationImage[];
}>();

const emit = defineEmits<{ goBack: [] }>();

const brandId = useBrandId();
const { data, goNext, saveData } =
  useMultiStepFormContext<TargetCustomerFormData>();
const { t } = useI18n();
const isLocked = computed(() => data.value.locked);

const images = ref<ImageStudioVariationImage[]>(props.initialImages ?? []);
const imagesWithNoLabels = computed(() =>
  images.value.filter((image) => !image.label),
);

const isDeleteModalOpen = ref(false);
const pendingImageToDelete = ref<ImageStudioVariationImage | undefined>(
  undefined,
);
const isAddModalOpen = ref(false);
const pendingLabelToAdd = ref<string | undefined>(undefined);
const labelLoaders = ref<string[]>([]);
const isUploadingVariation = ref(false);
const uploadErrorMessage = ref<string | undefined>(undefined);

const isCreateOverlayOpen = ref(false);
const createdStudioImages = ref<ImageStudioGeneratedImage[]>([]);
const isSelectingCreatedVariant = ref(false);
const createSelectionErrorMessage = ref<string | undefined>(undefined);

const isEditOverlayOpen = ref(false);
const editReferenceImage = ref<ImageStudioVariationImage | undefined>(
  undefined,
);
const editedStudioImages = ref<ImageStudioGeneratedImage[]>([]);
const isSelectingEditedVariant = ref(false);
const editSelectionErrorMessage = ref<string | undefined>(undefined);
const isSaving = ref(false);

const isStudioHelpVideoOpen = ref(false);

const EXTRA_SLOT_COUNT =
  TARGET_CUSTOMER_IMAGE_VARIATION_MAXIMUM_COUNT -
  TARGET_CUSTOMER_IMAGE_VARIATION_LABELS.length;

const visibleRequiredLabels = computed(() => {
  if (!isLocked.value) {
    return TARGET_CUSTOMER_IMAGE_VARIATION_LABELS;
  }

  return TARGET_CUSTOMER_IMAGE_VARIATION_LABELS.filter((label) =>
    images.value.some((image) => image.label === label.name),
  );
});

const extraSlotCount = computed(() =>
  isLocked.value ? imagesWithNoLabels.value.length : EXTRA_SLOT_COUNT,
);

const areAllLabelsFilled = computed(() => {
  return !TARGET_CUSTOMER_IMAGE_VARIATION_LABELS.every((label) =>
    images.value.some((image) => label.name === image.label),
  );
});

const isSubmitDisabled = computed(
  () => !isLocked.value && areAllLabelsFilled.value,
);

const isGenerateAllMissingDisabled = computed(
  () => !areAllLabelsFilled.value || labelLoaders.value.length > 0,
);

async function handleGoBack() {
  emit("goBack");
}

function handleAddVariation(label?: string) {
  if (isLocked.value) {
    return;
  }

  uploadErrorMessage.value = undefined;
  isAddModalOpen.value = true;
  pendingLabelToAdd.value = label;
}

async function handleDeleteImage(image?: ImageStudioVariationImage) {
  if (isLocked.value || !image) {
    return;
  }

  isDeleteModalOpen.value = true;
  pendingImageToDelete.value = image;
}

async function handleConfirmDelete() {
  if (isLocked.value || !pendingImageToDelete.value) {
    return;
  }

  const imageToDelete = pendingImageToDelete.value;

  if (imageToDelete.id !== undefined) {
    await BuyerPersonImagesApi.deleteVariant({
      brand_id: brandId,
      bperson_id: data.value.id,
      base_image_id: props.mainImage.image_id,
      variant_id: imageToDelete.id,
    });
  }

  // Remove from the array of images
  images.value = images.value.filter((image) => image !== imageToDelete);
  pendingImageToDelete.value = undefined;
}

async function handleEditImage(image?: ImageStudioVariationImage) {
  if (isLocked.value) {
    return;
  }

  if (!image?.image_id || !props.mainImage.image_id) {
    uploadErrorMessage.value = t("global.unexpected-error");
    return;
  }

  uploadErrorMessage.value = undefined;
  editSelectionErrorMessage.value = undefined;
  editReferenceImage.value = image;

  try {
    const { data: variant } = await BuyerPersonImagesApi.getVariant(
      brandId,
      data.value.id,
      image.image_id,
    );

    editedStudioImages.value = variant.images.map((editedImage) => ({
      id: editedImage.id,
      image_id: editedImage.image_id,
      image_url: editedImage.image_url,
      fetchBlob: true,
      prompt: editedImage.prompt || "",
    }));

    isEditOverlayOpen.value = true;
  } catch (error) {
    console.log(error);
    editReferenceImage.value = undefined;
    editedStudioImages.value = [];
    uploadErrorMessage.value = t("global.unexpected-error");
  }
}

async function handleAddVariationFile(image: ImageLibraryFile, label?: string) {
  if (isLocked.value) {
    return;
  }

  uploadErrorMessage.value = undefined;

  if (label) {
    setLabelLoading(label, true);
  } else {
    isUploadingVariation.value = true;
  }

  try {
    let variant: BuyerPersonMainImageVariant;

    if (image.raw) {
      const response = await BuyerPersonImagesApi.uploadVariantBinary({
        brand_id: brandId,
        bperson_id: data.value.id,
        base_image_id: props.mainImage.image_id,
        file: image,
        label,
      });

      variant = response.data;
    } else {
      const response = await BuyerPersonImagesApi.uploadVariantById({
        brand_id: brandId,
        bperson_id: data.value.id,
        base_image_id: props.mainImage.image_id,
        image_id: image.libraryId,
        label,
      });

      variant = response.data;
    }

    images.value = [
      ...images.value,
      {
        id: variant.id,
        image_id: variant.image_id,
        image_url: variant.image_url,
        image_blob: image,
        label: label ?? (variant.label || undefined),
        prompt: variant.prompt || undefined,
      },
    ];
  } catch (error) {
    console.log(error);
    uploadErrorMessage.value = t("global.unexpected-error");
  } finally {
    if (label) {
      setLabelLoading(label, false);
    } else {
      isUploadingVariation.value = false;
    }
  }
}

function setLabelLoading(label: string, loading: boolean) {
  if (loading) {
    if (!labelLoaders.value.includes(label)) {
      labelLoaders.value.push(label);
    }
  } else {
    labelLoaders.value = labelLoaders.value.filter(
      (labelB) => label !== labelB,
    );
  }
}

async function generateVariantsForLabels(labels: string[]) {
  if (isLocked.value || labels.length === 0) {
    return;
  }

  uploadErrorMessage.value = undefined;
  labels.forEach((label) => setLabelLoading(label, true));

  try {
    const response = await BuyerPersonImagesApi.startGenerateVariantsJob({
      brand_id: brandId,
      bperson_id: data.value.id,
      image_id: props.mainImage.image_id,
      labels,
    });

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

    if (result.status === "FAILED") {
      throw new UnidentifiedError();
    }

    const { variants } = (
      await BuyerPersonImagesApi.getMainImageVariants(
        brandId,
        data.value.id,
        props.mainImage.image_id,
      )
    ).data;

    const unlabeled = images.value.filter((image) => !image.label);

    images.value = [
      ...variants.map(({ id, image_id, image_url, prompt, label }) => ({
        id,
        image_id,
        image_url,
        prompt,
        label,
      })),
      ...unlabeled,
    ];
  } catch (error) {
    console.log(error);
    uploadErrorMessage.value = t("global.unexpected-error");
  } finally {
    labels.forEach((label) => setLabelLoading(label, false));
  }
}

async function handleGenerateVariationWithLuca(label: string) {
  await generateVariantsForLabels([label]);
}

async function handleWriteVariationToLuca() {
  if (isLocked.value) {
    return;
  }

  if (!props.mainImage.image_id) {
    uploadErrorMessage.value = t("global.unexpected-error");
    return;
  }

  uploadErrorMessage.value = undefined;
  createSelectionErrorMessage.value = undefined;

  try {
    const { variants } = (
      await BuyerPersonImagesApi.getMainImageVariants(
        brandId,
        data.value.id,
        props.mainImage.image_id,
        { unlabeled: true },
      )
    ).data;

    createdStudioImages.value = variants.map((variant) => ({
      id: variant.id,
      image_id: variant.image_id,
      image_url: variant.image_url,
      fetchBlob: true,
      prompt: variant.prompt || "",
    }));

    isCreateOverlayOpen.value = true;
  } catch (error) {
    console.log(error);
    uploadErrorMessage.value = t("global.unexpected-error");
  }
}

async function handleGenerateVariationWithNoLabel(
  options: ImageStudioGenerateFnOptions,
): Promise<ImageStudioGeneratedImage[]> {
  if (isLocked.value || !props.mainImage.image_id) {
    throw new UnidentifiedError();
  }

  const existingIds = new Set(
    createdStudioImages.value.map((image) => image.id),
  );

  const response = await BuyerPersonImagesApi.startGenerateCustomVariantsJob({
    brand_id: brandId,
    bperson_id: data.value.id,
    // normal / moreLikeThis → no base image; edit → image being edited
    main_image_id:
      options.mode === "edit" ? options.targetImage?.image_id : undefined,
    custom_prompt: options.prompt ?? "",
    n_variants: options.variations,
    photography_effect: options.photographyEffect?.name,
    product_id: options.targetProduct?.id,
    reference_images: options.referenceImages,
    visual_style: options.visualStyle?.name,
  });

  const jobId = response.data.job_id;
  const result = await pooling(
    async () => {
      const { data: jobResult } =
        await BuyerPersonImagesApi.getGenerateMainImageListJobResult(jobId);

      return jobResult;
    },
    (jobResult) => jobResult.status === "DONE" || jobResult.status === "FAILED",
    TARGET_CUSTOMER_IMAGE_JOB_POLLING_INTERVAL_MS,
    { timeoutMs: TARGET_CUSTOMER_IMAGE_JOB_TIMEOUT_MS },
  );

  if (result.status === "FAILED") {
    throw new UnidentifiedError();
  }

  const { variants } = (
    await BuyerPersonImagesApi.getMainImageVariants(
      brandId,
      data.value.id,
      props.mainImage.image_id,
      { unlabeled: true },
    )
  ).data;

  const newImages = variants
    .filter((variant) => !existingIds.has(variant.id))
    .map<ImageStudioGeneratedImage>((variant) => ({
      id: variant.id,
      image_id: variant.image_id,
      image_url: variant.image_url,
      fetchBlob: true,
      prompt: variant.prompt || "",
    }));

  if (newImages.length === 0) {
    throw new UnidentifiedError();
  }

  return newImages;
}

async function handleSelectVariationWithNoLabel(
  newImage: ImageStudioGeneratedImage,
) {
  if (isLocked.value || !props.mainImage.image_id || !newImage.image_id) {
    throw new UnidentifiedError();
  }

  try {
    isSelectingCreatedVariant.value = true;
    createSelectionErrorMessage.value = undefined;

    await BuyerPersonImagesApi.selectVariant({
      brand_id: brandId,
      bperson_id: data.value.id,
      main_image_id: props.mainImage.image_id,
      variant_image_id: newImage.image_id,
    });

    images.value = [
      ...images.value,
      {
        id: newImage.id,
        image_id: newImage.image_id,
        image_url: newImage.image_url,
        prompt: newImage.prompt,
      },
    ];

    isCreateOverlayOpen.value = false;
    createdStudioImages.value = [];
  } catch (error) {
    console.log(error);
    createSelectionErrorMessage.value = t("global.unexpected-error");
  } finally {
    isSelectingCreatedVariant.value = false;
  }
}

async function handleGenerateEditedVariationFromStudio(
  options: ImageStudioGenerateFnOptions,
): Promise<ImageStudioGeneratedImage[]> {
  if (
    isLocked.value ||
    !editReferenceImage.value?.image_id ||
    !props.mainImage.image_id
  ) {
    throw new UnidentifiedError();
  }

  const response = await BuyerPersonImagesApi.startEditVariantJob({
    brand_id: brandId,
    bperson_id: data.value.id,
    main_image_id: props.mainImage.image_id,
    // normal / moreLikeThis → no base image; edit → image being edited
    base_image_id:
      options.mode === "edit" ? options.targetImage?.image_id : undefined,
    custom_prompt: options.prompt ?? "",
    n_variants: options.variations,
    photography_effect: options.photographyEffect?.name,
    product_id: options.targetProduct?.id,
    reference_images: options.referenceImages,
    label: editReferenceImage.value.label,
    visual_style: options.visualStyle?.name,
  });

  const jobId = response.data.job_id;
  const result = await pooling(
    async () => {
      const { data: jobResult } =
        await BuyerPersonImagesApi.getGenerateMainImageListJobResult(jobId);

      return jobResult;
    },
    (jobResult) => jobResult.status === "DONE" || jobResult.status === "FAILED",
    TARGET_CUSTOMER_IMAGE_JOB_POLLING_INTERVAL_MS,
    { timeoutMs: TARGET_CUSTOMER_IMAGE_JOB_TIMEOUT_MS },
  );

  if (result.status === "FAILED") {
    throw new UnidentifiedError();
  }

  const existingIds = new Set(
    editedStudioImages.value.map((image) => image.id),
  );
  const { data: variant } = await BuyerPersonImagesApi.getVariant(
    brandId,
    data.value.id,
    editReferenceImage.value.image_id,
  );

  const newImages = variant.images
    .filter((image) => !existingIds.has(image.id))
    .map<ImageStudioGeneratedImage>((image) => ({
      id: image.id,
      image_id: image.image_id,
      image_url: image.image_url,
      fetchBlob: true,
      prompt: image.prompt || "",
    }));

  if (newImages.length === 0) {
    throw new UnidentifiedError();
  }

  return newImages;
}

async function handleSelectVariationEditedFromStudio(
  newImage: ImageStudioGeneratedImage,
) {
  if (
    isLocked.value ||
    !editReferenceImage.value ||
    !props.mainImage.image_id ||
    !newImage.image_id
  ) {
    throw new UnidentifiedError();
  }

  try {
    isSelectingEditedVariant.value = true;
    editSelectionErrorMessage.value = undefined;

    await BuyerPersonImagesApi.selectVariant({
      brand_id: brandId,
      bperson_id: data.value.id,
      main_image_id: props.mainImage.image_id,
      variant_image_id: newImage.image_id,
    });

    images.value = images.value.map((image) =>
      image.id !== undefined && image.id === editReferenceImage.value?.id
        ? {
            ...image,
            id: newImage.id,
            image_id: newImage.image_id,
            image_url: newImage.image_url,
            prompt: newImage.prompt,
            image_blob: undefined,
          }
        : image,
    );

    isEditOverlayOpen.value = false;
    editReferenceImage.value = undefined;
    editedStudioImages.value = [];
  } catch (error) {
    console.log(error);
    editSelectionErrorMessage.value = t("global.unexpected-error");
  } finally {
    isSelectingEditedVariant.value = false;
  }
}

async function handleGenerateAllMissingVariations() {
  const missingLabels = TARGET_CUSTOMER_IMAGE_VARIATION_LABELS.filter(
    (label) => !images.value.some((image) => image.label === label.name),
  ).map((label) => label.name);

  await generateVariantsForLabels(missingLabels);
}

async function handleSaveAndGenerateSummary() {
  if (isLocked.value) {
    goNext({ isDirty: false });
    return;
  }

  if (!props.mainImage.image_id || isSubmitDisabled.value) {
    return;
  }

  isSaving.value = true;
  uploadErrorMessage.value = undefined;

  try {
    await BuyerPersonImagesApi.selectMainImage({
      brand_id: brandId,
      bperson_id: data.value.id,
      image_id: props.mainImage.image_id,
    });

    const response = await BuyerPersonImagesApi.completeImages({
      brand_id: brandId,
      bperson_id: data.value.id,
    });

    saveData({ ...response.data });
    goNext({ isDirty: false });
  } catch (error) {
    console.log(error);
    uploadErrorMessage.value = t("global.unexpected-error");
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <FormStepLayout as="div" :maxWidth="1100">
    <!-- TODO: add help video URL later -->
    <PageTitle>
      {{
        $t("buyer-person.image.variations-overlay.collection-title", {
          name: data.name,
        })
      }}

      <template #description>
        {{
          $t("buyer-person.image.variations-overlay.description", {
            min: TARGET_CUSTOMER_IMAGE_VARIATION_LABELS.length,
            extra: EXTRA_SLOT_COUNT,
          })
        }}
      </template>
    </PageTitle>

    <div
      class="tw:flex tw:flex-col tw:gap-[30px] tw:lg:flex-row tw:lg:items-start"
    >
      <CardBase
        class="tw:flex tw:flex-col tw:gap-3 tw:p-4 tw:lg:shrink-0 tw:lg:basis-[406px]"
      >
        <h2 class="tw:text-lg tw:font-bold">
          {{ $t("buyer-person.image.variations-overlay.main-image") }}
        </h2>

        <div
          class="tw:aspect-square tw:overflow-hidden tw:rounded-[10px] tw:bg-gray-500"
        >
          <ImgFile
            :src="mainImage.image_blob ?? mainImage.image_url"
            class="tw:h-full tw:w-full tw:object-contain"
          />
        </div>

        <p v-if="mainImage.prompt" class="tw:text-xs tw:text-gray-500">
          {{ mainImage.prompt }}
        </p>
      </CardBase>

      <CardBase
        class="tw:flex tw:grow tw:flex-col tw:gap-4 tw:p-4 tw:lg:self-start"
      >
        <div
          class="tw:flex tw:flex-col tw:justify-between tw:gap-2 tw:xl:flex-row"
        >
          <p class="tw:text-sm tw:text-secondary-text">
            {{
              $t("buyer-person.image.variations-overlay.variations-description")
            }}
          </p>

          <Link
            v-if="!isLocked"
            is="button"
            type="button"
            leftIcon="custom:hi-luca"
            class="tw:text-sm tw:font-medium"
            :disabled="isGenerateAllMissingDisabled"
            @click="handleGenerateAllMissingVariations"
          >
            {{
              $t("buyer-person.image.variations-overlay.generate-all-missing")
            }}
          </Link>
        </div>

        <Alert v-if="uploadErrorMessage" type="error" autoScroll>
          {{ uploadErrorMessage }}
        </Alert>

        <!-- TODO: Grid of variations -->
        <div
          class="tw:grid tw:grid-cols-1 tw:gap-4 tw:xl:grid-cols-2 tw:2xl:grid-cols-3"
        >
          <ImageStudioVariationSlot
            v-for="label in visibleRequiredLabels"
            :label="label.name"
            :previewImage="label.preview_image_url"
            :image="images.find((image) => image.label === label.name)"
            :isGenerating="labelLoaders.includes(label.name)"
            :readOnly="isLocked"
            @add="handleAddVariation(label.name)"
            @delete="
              handleDeleteImage(
                images.find((image) => image.label === label.name),
              )
            "
            @edit="
              handleEditImage(
                images.find((image) => image.label === label.name),
              )
            "
          />

          <ImageStudioVariationSlot
            v-for="index in extraSlotCount"
            :image="imagesWithNoLabels?.[index - 1]"
            :isGenerating="
              !imagesWithNoLabels?.[index - 1] &&
              isUploadingVariation &&
              index === imagesWithNoLabels.length + 1
            "
            :readOnly="isLocked"
            @add="handleAddVariation()"
            @delete="handleDeleteImage(imagesWithNoLabels?.[index - 1])"
            @edit="handleEditImage(imagesWithNoLabels?.[index - 1])"
          />
        </div>
      </CardBase>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="handleGoBack">
          {{ $t("buyer-person.image.variations-overlay.back-action") }}
        </ButtonGoBack>

        <Tooltip :disabled="!isSubmitDisabled" placement="top" :maxWidth="225">
          <Button
            type="button"
            icon="tabler-arrow-right"
            :disabled="isSubmitDisabled"
            :isLoading="isSaving"
            @click="handleSaveAndGenerateSummary"
          >
            {{
              isLocked
                ? $t("global.next")
                : $t(
                    "buyer-person.image.variations-overlay.save-and-generate-summary",
                  )
            }}
          </Button>

          <template #content>
            {{
              $t("buyer-person.image.variations-overlay.save-tooltip", {
                min: TARGET_CUSTOMER_IMAGE_VARIATION_LABELS.length,
              })
            }}
          </template>
        </Tooltip>
      </WizardCardActions>
    </template>

    <!-- Delete confirmation modal -->
    <ModalDelete
      v-if="pendingImageToDelete"
      v-model="isDeleteModalOpen"
      :confirmFn="handleConfirmDelete"
      :imgSrc="
        pendingImageToDelete.image_blob ?? pendingImageToDelete.image_url
      "
    >
      <template #title>
        {{ $t("buyer-person.image.variations-overlay.delete.title") }}
      </template>

      <template #warning>
        {{ $t("buyer-person.image.variations-overlay.delete.warning") }}
      </template>
    </ModalDelete>

    <!-- Modal for adding new variations -->
    <ImageStudioVariationAddModal
      v-if="isAddModalOpen"
      v-model="isAddModalOpen"
      :label="pendingLabelToAdd"
      @addFile="handleAddVariationFile"
      @generateWithLuca="handleGenerateVariationWithLuca"
      @writeToLuca="handleWriteVariationToLuca"
    />

    <!-- Image studio overlay: Create mode (no label) -->
    <ImageStudioOverlay
      v-if="isCreateOverlayOpen"
      v-model="isCreateOverlayOpen"
      v-model:images="createdStudioImages"
      :referenceImage="mainImage.image_blob || mainImage.image_url"
      :referenceImagePrompt="mainImage.prompt"
      :brandId="brandId"
      enableProductAttachment
      enableEditing
      enableMoreLikeThis
      enableAddReference
      enableVariations
      enablePhotographicEffects
      enableStyle
      enableImproveResultsModal
      initialMode="edit"
      :initialTargetImage="{
        id: 0,
        image_id: mainImage.image_id,
        image_url: mainImage.image_url,
        prompt: mainImage.prompt,
      }"
      :generateFn="handleGenerateVariationWithNoLabel"
      :selectButtonProps="{
        isLoading: isSelectingCreatedVariant,
      }"
      @select="handleSelectVariationWithNoLabel"
    >
      <template #headerTitle>
        {{
          $t("buyer-person.image.variations-overlay.create-studio.header-title")
        }}
      </template>

      <template #headerSubtitle>
        {{ data.name }}
      </template>

      <template #title>
        {{ $t("buyer-person.image.variations-overlay.create-studio.title") }}
      </template>

      <template #description>
        <i18n-t
          keypath="buyer-person.image.variations-overlay.create-studio.description"
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

      <template #selectLabel>
        {{
          $t("buyer-person.image.variations-overlay.create-studio.select-label")
        }}
      </template>

      <template #selectionTitle>
        {{
          $t(
            "buyer-person.image.variations-overlay.create-studio.selection-title",
          )
        }}
      </template>

      <template #selectionDescription>
        {{
          $t(
            "buyer-person.image.variations-overlay.create-studio.selection-description",
          )
        }}
      </template>

      <template #selectionAlert>
        <Alert v-if="createSelectionErrorMessage" type="error" autoScroll>
          {{ createSelectionErrorMessage }}
        </Alert>
      </template>

      <template #galleryDescription>
        {{ $t("buyer-person.image.variations-overlay.gallery-description") }}
      </template>
    </ImageStudioOverlay>

    <!-- Image studio overlay: Edit mode -->
    <ImageStudioOverlay
      v-if="isEditOverlayOpen && editReferenceImage"
      v-model="isEditOverlayOpen"
      v-model:images="editedStudioImages"
      :referenceImage="
        editReferenceImage.image_blob || editReferenceImage.image_url
      "
      :referenceImagePrompt="editReferenceImage.prompt"
      :brandId="brandId"
      enableProductAttachment
      enableEditing
      enableMoreLikeThis
      enableAddReference
      enableVariations
      enablePhotographicEffects
      enableStyle
      enableImproveResultsModal
      initialMode="edit"
      :initialTargetImage="{
        id: editReferenceImage.id,
        image_id: editReferenceImage.image_id,
        image_url: editReferenceImage.image_url,
        prompt: editReferenceImage.prompt,
      }"
      :generateFn="handleGenerateEditedVariationFromStudio"
      :selectButtonProps="{
        isLoading: isSelectingEditedVariant,
      }"
      @select="handleSelectVariationEditedFromStudio"
    >
      <template #headerTitle>
        {{
          $t("buyer-person.image.variations-overlay.edit-studio.header-title", {
            variation: t(
              `buyer-person.image.variations.${editReferenceImage.label}.title`,
            ),
          })
        }}
      </template>

      <template #headerSubtitle>
        {{ data.name }}
      </template>

      <template #title>
        {{
          $t("buyer-person.image.variations-overlay.edit-studio.title", {
            variation: t(
              `buyer-person.image.variations.${editReferenceImage.label}.title`,
            ),
          })
        }}
      </template>

      <template #description>
        <i18n-t
          keypath="buyer-person.image.variations-overlay.edit-studio.description"
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

      <template #selectLabel>
        {{
          $t("buyer-person.image.variations-overlay.edit-studio.select-label")
        }}
      </template>

      <template #selectionTitle>
        {{
          $t(
            "buyer-person.image.variations-overlay.edit-studio.selection-title",
            {
              variation: t(
                `buyer-person.image.variations.${editReferenceImage.label}.title`,
              ),
            },
          )
        }}
      </template>

      <template #selectionDescription>
        {{
          $t(
            "buyer-person.image.variations-overlay.edit-studio.selection-description",
          )
        }}
      </template>

      <template #selectionAlert>
        <Alert v-if="editSelectionErrorMessage" type="error" autoScroll>
          {{ editSelectionErrorMessage }}
        </Alert>
      </template>

      <template #galleryDescription>
        {{ $t("buyer-person.image.variations-overlay.gallery-description") }}
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
  </FormStepLayout>
</template>
