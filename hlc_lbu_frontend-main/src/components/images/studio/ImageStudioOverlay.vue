<script setup lang="ts">
import {
  ImageStudioDeleteFn,
  ImageStudioGeneratedImage,
  ImageStudioGenerateFn,
  ImageStudioGenerateMode,
  ImageStudioGenerateError,
} from "@/components/images/studio/types";
import FullScreenOverlay from "@/components/modals/base/FullScreenOverlay.vue";
import { ProductData } from "@/services/ProductsApi";
import UtilsApi from "@/services/UtilsApi";
import { downloadStudioImage } from "@/components/images/studio/utils";
import { ButtonProps } from "@/components/buttons/base/Button.vue";

const props = defineProps<{
  referenceImage?: string | ImageLibraryFile | Blob;
  referenceImagePrompt?: string;
  brandId?: number;
  initialSelectedImageId?: number;
  initialMode?: ImageStudioGenerateMode;
  initialTargetImage?: ImageStudioGeneratedImage;
  deleteFn?: ImageStudioDeleteFn;
  generateFn?: ImageStudioGenerateFn;
  selectButtonProps?: ButtonProps;
  isContentLoading?: boolean;
  readOnly?: boolean;
  enableEditing?: boolean;
  enableMoreLikeThis?: boolean;
  enableAddReference?: boolean;
  enableVariations?: boolean;
  enablePhotographicEffects?: boolean;
  enableStyle?: boolean;
  enableProductAttachment?: boolean;
  enableExpandZoom?: boolean;
  /** Shows the "Didn't like the results?" link above the generated images */
  enableImproveResultsModal?: boolean;
  /** Allows clicking Generate with an empty prompt */
  allowEmptyPrompt?: boolean;
}>();

const emit = defineEmits<{
  select: [image: ImageStudioGeneratedImage];
  unselect: [];
}>();

const isOpen = defineModel<boolean>({ required: true });
const generatedImages = defineModel<ImageStudioGeneratedImage[]>("images", {
  default: () => [],
});

const { t } = useI18n();
const imageLibraryStore = useImageLibraryStore();

const overlayRef = ref<InstanceType<typeof FullScreenOverlay>>();
const libraryTargetId = ref(Symbol("ImageLibraryModal"));

const isDirty = ref(false);

const prompt = ref<string | undefined>(undefined);
const referenceImages = ref<ImageLibraryFile[]>([]);
const variations = ref(4);
const expandZoom = ref<ImageStudioExpandZoom>();
const photographyEffect = ref<ImageStudioPhotographicEffect | undefined>(
  undefined,
);
const visualStyle = ref<ImageStudioVisualStyle | undefined>(undefined);
const targetProduct = ref<ProductData | undefined>(undefined);

const mode = ref<ImageStudioGenerateMode>(props.initialMode ?? "normal");

const targetImage = ref<ImageStudioGeneratedImage | undefined>(
  props.initialTargetImage,
);
const selectedImage = ref<ImageStudioGeneratedImage | undefined>(
  props.initialSelectedImageId
    ? generatedImages.value.find(
        (image) => image.id === props.initialSelectedImageId,
      )
    : undefined,
);

watch(selectedImage, () => {
  generalErrorMessage.value = undefined;
});

const isLibraryOpen = ref(false);
const arePhotographicEffectsOpen = ref(false);
const areVisualStylesOpen = ref(false);
const createdVisualStyles = ref<ImageStudioVisualStyle[]>([]);
const isProductsModalOpen = ref(false);
const isDeleteModalOpen = ref(false);
const pendingImageToDelete = ref<ImageStudioGeneratedImage | undefined>(
  undefined,
);
const isPreviewModalOpen = ref(false);
const imagePreview = ref<ImageStudioGeneratedImage | undefined>(undefined);
const isImproveResultsModalOpen = ref(false);

const isGenerating = ref(false);
const variationCountBeingGenerated = ref(0);
const generalErrorMessage = ref<string | undefined>(undefined);

const isGenerateButtonDisabled = computed(
  () => !props.allowEmptyPrompt && !prompt.value,
);

const VARIATIONS_MAX = 4;
const VARIATIONS_STACK_ICONS = {
  1: "tabler:stack-0",
  2: "tabler:stack",
  3: "tabler:stack-2",
  4: "tabler:stack-3",
};

const fetchingBlobIds = new Set<number>();

async function fetchMissingImageBlobs() {
  const imagesToFetch = [...generatedImages.value]
    .reverse()
    .filter(
      (image) =>
        image.fetchBlob && !image.image_blob && !fetchingBlobIds.has(image.id),
    );

  if (imagesToFetch.length === 0) {
    return;
  }

  imagesToFetch.forEach((image) => fetchingBlobIds.add(image.id));

  await Promise.all(
    imagesToFetch.map(async (image) => {
      try {
        const blob = await UtilsApi.getBinaryFromPresignedUrl(image.image_url);

        generatedImages.value = generatedImages.value.map((imageB) =>
          imageB.id === image.id
            ? { ...imageB, image_blob: blob, fetchBlob: false }
            : imageB,
        );
      } finally {
        fetchingBlobIds.delete(image.id);
      }
    }),
  );
}

// Download blobs for images that still need them (on mount and when the list updates)
watch(
  generatedImages,
  () => {
    fetchMissingImageBlobs();
  },
  { immediate: true, deep: true },
);

// Mark as dirty if any field changes
watch([prompt], () => {
  isDirty.value = true;
});

async function handleClose() {
  // Save locking
  if ((await useSaveLockingStore().execute()) === "cancel") return;

  isOpen.value = false;
}

function scrollToBottom() {
  // Scroll to botton
  if (overlayRef.value?.element) {
    scrollElementToItsBottom(overlayRef.value.element);
  }
}

// Scroll to bottom on mount
onMounted(() => {
  scrollToBottom();
});

// Scroll to bottom when the content loader disappears
watch(
  () => props.isContentLoading,
  async (isLoading, wasLoading) => {
    if (wasLoading && !isLoading) {
      await nextTick();
      scrollToBottom();
    }
  },
);

async function handleUnselect() {
  selectedImage.value = undefined;
  emit("unselect");
}

async function handleGenerate() {
  if (props.readOnly || !props.generateFn) {
    return;
  }

  try {
    generalErrorMessage.value = undefined;
    isGenerating.value = true;
    variationCountBeingGenerated.value = variations.value;

    // Scroll to bottom
    await nextTick();
    scrollToBottom();

    // Call the generate function (returns only newly generated images)
    const newImages = await props.generateFn({
      prompt: prompt.value,
      variations: variations.value,
      mode: mode.value,
      targetImage: targetImage.value,
      referenceImages: referenceImages.value,
      photographyEffect: photographyEffect.value,
      visualStyle: visualStyle.value,
      targetProduct: targetProduct.value,
      expandZoom: expandZoom.value,
    });

    // Check if any images were generated
    if (newImages.length === 0) {
      throw new Error("No images were generated.");
    }

    // Append the newly generated images
    generatedImages.value = [...generatedImages.value, ...newImages];
  } catch (error) {
    console.error("Failed to generate images:", error);
    generalErrorMessage.value =
      error instanceof ImageStudioGenerateError
        ? error.message
        : t("global.unexpected-error");
  } finally {
    isGenerating.value = false;
    variationCountBeingGenerated.value = 0;
  }
}

// Store the selected reference image from the library
watch(
  () => imageLibraryStore.selectedFile,
  async (file) => {
    if (!file) return;

    if (
      imageLibraryStore.lastTarget &&
      imageLibraryStore.lastTarget === libraryTargetId.value
    ) {
      referenceImages.value = [...referenceImages.value, file];
      isLibraryOpen.value = false;
    }
  },
);

function handleOpenLibrary() {
  imageLibraryStore.setActiveTarget(libraryTargetId.value);
  isLibraryOpen.value = true;
}

function handleRemoveReferenceImage(image: ImageLibraryFile) {
  referenceImages.value = referenceImages.value.filter(
    (referenceImage) => referenceImage !== image,
  );
}

function handleSelectVariationCount(
  variationCount: number,
  closeDropdown: Function,
) {
  variations.value = variationCount;
  closeDropdown();
}

function handleOpenPhotographyEffects() {
  arePhotographicEffectsOpen.value = true;
}

function handleSelectPhotographyEffect(effect: ImageStudioPhotographicEffect) {
  arePhotographicEffectsOpen.value = false;
  photographyEffect.value = effect;
}

function handleRemovePhotographicEffect() {
  photographyEffect.value = undefined;
}

function handleOpenVisualStyles() {
  areVisualStylesOpen.value = true;
}

function handleSelectVisualStyle(style: ImageStudioVisualStyle) {
  areVisualStylesOpen.value = false;
  visualStyle.value = style;
}

function handleRemoveVisualStyle() {
  visualStyle.value = undefined;
}

function handleCreateVisualStyle(style: ImageStudioVisualStyle) {
  createdVisualStyles.value = [...createdVisualStyles.value, style];
}

function handleAddProduct() {
  isProductsModalOpen.value = true;
}

function handleSelectProduct(product: ProductData) {
  targetProduct.value = product;
}

function handleRemoveProduct() {
  targetProduct.value = undefined;
}

async function handleMoreLikeThisImage(image: ImageStudioGeneratedImage) {
  if (props.readOnly) {
    return;
  }

  targetImage.value = image;
  prompt.value = image.prompt;
  mode.value = "moreLikeThis";
}

async function handleEditImage(image: ImageStudioGeneratedImage) {
  if (props.readOnly) {
    return;
  }

  // Unselect current image
  selectedImage.value = undefined;

  // Close preview modal
  isPreviewModalOpen.value = false;

  // Reset prompt
  if (mode.value === "moreLikeThis") {
    prompt.value = undefined;
  }

  targetImage.value = image;
  mode.value = "edit";
}

async function handleDeleteImage(image: ImageStudioGeneratedImage) {
  if (props.readOnly) {
    return;
  }

  isDeleteModalOpen.value = true;
  pendingImageToDelete.value = image;
}

async function handleConfirmDelete() {
  if (props.readOnly || !pendingImageToDelete.value) {
    return;
  }

  const imageIdToDelete = pendingImageToDelete.value.id;

  // Call delete endpoint
  await props.deleteFn?.(pendingImageToDelete.value);

  // Exit out of edit mode
  if (targetImage.value?.id === imageIdToDelete) {
    targetImage.value = undefined;
    mode.value = "normal";
  }

  // Unselect image
  if (selectedImage.value?.id === imageIdToDelete) {
    selectedImage.value = undefined;
  }

  // Close preview modal
  isPreviewModalOpen.value = false;

  // Remove from the array of images
  generatedImages.value = generatedImages.value.filter(
    (image) => image.id !== imageIdToDelete,
  );
  pendingImageToDelete.value = undefined;
}

function handlePreviewImage(image: ImageStudioGeneratedImage) {
  isPreviewModalOpen.value = true;
  imagePreview.value = image;
}

async function handleRemoveTargetImage() {
  targetImage.value = undefined;
  mode.value = "normal";
}

function handleOpenImproveResultsModal() {
  isImproveResultsModalOpen.value = true;
}
</script>

<template>
  <FullScreenOverlay
    ref="overlayRef"
    v-model="isOpen"
    mode="navbar"
    fallbackFocusToForeground
  >
    <GenericSubLayout>
      <template #headerBackAction>
        <button type="button" @click="handleClose">
          <Icon icon="tabler-arrow-left" class="tw:text-2xl" />
        </button>
      </template>

      <template #headerLeft>
        <h2>
          <span class="tw:line-clamp-1 tw:font-bold">
            <slot name="headerTitle" />
            <br />
          </span>

          <span
            v-if="$slots.headerSubtitle"
            class="tw:text-sm tw:text-secondary-text"
          >
            <slot name="headerSubtitle" />
          </span>
        </h2>
      </template>

      <template #headerRight>
        <HelpButton size="sm" />
      </template>

      <template #custom>
        <div
          class="tw:flex tw:grow tw:flex-col tw:bg-gray-200"
          :class="{
            'tw:justify-end': !isContentLoading,
            'tw:justify-center': isContentLoading,
          }"
        >
          <Container
            v-if="isContentLoading"
            :maxWidth="1100"
            class="tw:flex tw:flex-col tw:gap-10 tw:py-6"
          >
            <CircleLoaderDefault />
          </Container>
          <Container
            v-else
            :maxWidth="1100"
            class="tw:flex tw:flex-col tw:gap-10 tw:py-6"
          >
            <!-- Reference image -->
            <CardBase
              v-if="referenceImage"
              color="secondary"
              class="tw:mx-auto tw:flex tw:max-w-[200px] tw:flex-col tw:items-center tw:gap-6 tw:bg-gray-100! tw:p-4 tw:sm:flex-row"
              borderless
              style="max-width: 800px"
            >
              <div
                class="tw:aspect-square tw:shrink-0 tw:overflow-hidden tw:rounded-[10px] tw:bg-gray-500 tw:sm:h-[200px]"
              >
                <ImgFile
                  :src="referenceImage"
                  class="tw:h-full tw:w-full tw:object-contain"
                />
              </div>

              <div v-if="referenceImagePrompt">
                <h2 class="tw:mb-3 tw:text-lg tw:font-bold">
                  {{ $t("image-studio.main-image") }}
                </h2>

                <p class="tw:text-xs tw:text-secondary-text tw:italic">
                  {{ referenceImagePrompt }}
                </p>
              </div>
            </CardBase>

            <!-- Header -->
            <div
              v-if="$slots.title || $slots.description"
              style="max-width: 611px"
              class="tw:mx-auto tw:text-center"
            >
              <h1
                v-if="$slots.title"
                class="tw:mb-3 tw:text-3xl tw:font-bold tw:last:mb-0"
              >
                <slot name="title" />
              </h1>

              <p
                v-if="$slots.description"
                class="tw:font-medium tw:text-secondary-text"
              >
                <slot name="description" />
              </p>
            </div>

            <!-- Generated images -->
            <CardBase
              v-if="
                generatedImages.length > 0 || variationCountBeingGenerated > 0
              "
              class="tw:flex tw:flex-col tw:gap-4 tw:p-4"
            >
              <div
                v-if="
                  $slots.galleryDescription ||
                  (enableImproveResultsModal && !readOnly)
                "
                class="tw:flex tw:flex-col tw:justify-between tw:text-sm tw:md:flex-row tw:md:gap-3"
              >
                <p
                  v-if="$slots.galleryDescription"
                  class="tw:text-secondary-text"
                >
                  <slot name="galleryDescription" />
                </p>

                <Link
                  v-if="enableImproveResultsModal && !readOnly"
                  is="button"
                  underline
                  @click="handleOpenImproveResultsModal"
                >
                  {{ $t("image-studio.didnt-like-results") }}
                </Link>
              </div>

              <div
                class="tw:grid tw:grid-cols-1 tw:gap-4 tw:sm:grid-cols-2 tw:lg:grid-cols-4"
              >
                <ImageStudioGenerationCard
                  v-for="image in generatedImages"
                  v-model:selectedImage="selectedImage"
                  :image="image"
                  :disabled="isGenerating"
                  :readOnly="readOnly"
                  :enableEditing="enableEditing"
                  :enableMoreLikeThis="enableMoreLikeThis"
                  @moreLikeThis="handleMoreLikeThisImage(image)"
                  @edit="handleEditImage(image)"
                  @delete="handleDeleteImage(image)"
                  @preview="handlePreviewImage(image)"
                />

                <ImageStudioLoadingCard
                  v-for="_value in variationCountBeingGenerated"
                />
              </div>
            </CardBase>

            <!-- Footer -->
            <CardBase
              v-if="selectedImage || !readOnly"
              class="tw:sticky tw:bottom-6"
              :outlineColor="
                targetImage && !selectedImage ? 'primary' : 'default'
              "
              :borderWidth="2"
            >
              <!-- Selected image -->
              <div
                v-if="selectedImage"
                class="tw:flex tw:flex-col tw:gap-4 tw:p-6"
              >
                <div
                  v-if="selectedImage"
                  class="tw:flex tw:flex-col tw:gap-3 tw:lg:flex-row"
                >
                  <div class="tw:grow">
                    <h3
                      v-if="$slots.selectionTitle"
                      class="tw:mb-2 tw:text-2xl tw:font-bold"
                    >
                      <slot name="selectionTitle" />
                    </h3>

                    <p
                      v-if="$slots.selectionDescription"
                      class="tw:font-medium tw:text-secondary-text"
                    >
                      <slot name="selectionDescription" />
                    </p>
                  </div>

                  <div class="tw:flex tw:items-center tw:justify-end tw:gap-3">
                    <Button
                      v-if="
                        $slots.selectLabel &&
                        (!readOnly || selectedImage.has_variants)
                      "
                      type="button"
                      @click="emit('select', selectedImage)"
                      v-bind="selectButtonProps"
                    >
                      <slot name="selectLabel" :image="selectedImage" />
                    </Button>

                    <!-- Download button -->
                    <Button
                      type="button"
                      icon="tabler:download"
                      variant="outlined"
                      color="secondary"
                      @click="downloadStudioImage(selectedImage)"
                    />

                    <!-- Delete button -->
                    <Button
                      v-if="!readOnly"
                      type="button"
                      icon="tabler:trash"
                      variant="outlined"
                      color="secondary"
                      :disabled="isGenerating"
                      @click="handleDeleteImage(selectedImage)"
                    />

                    <button type="button" @click="handleUnselect">
                      <Icon icon="tabler:x" class="tw:text-[24px]" />
                    </button>
                  </div>
                </div>

                <slot name="selectionAlert" />
              </div>
              <!-- Chat/prompt -->
              <div
                v-else-if="!readOnly"
                class="tw:flex tw:flex-col tw:gap-2.5 tw:p-3"
              >
                <!-- Reference images preview -->
                <div
                  v-if="referenceImages.length > 0 || mode !== 'normal'"
                  class="tw:flex tw:flex-wrap tw:items-center tw:gap-3.5"
                >
                  <template v-if="mode !== 'normal'">
                    <div
                      class="tw:flex tw:gap-1 tw:rounded-full tw:bg-primary-100 tw:px-2.5 tw:py-1 tw:text-sm tw:font-medium tw:text-primary-900"
                    >
                      <template v-if="mode === 'edit'">
                        {{ $t("image-studio.edit-mode") }}
                      </template>
                      <template v-if="mode === 'moreLikeThis'">
                        {{ $t("image-studio.more-like-this-mode") }}
                      </template>

                      <button type="button" @click="handleRemoveTargetImage">
                        <Icon icon="tabler:x" class="tw:text-[14px]" />
                      </button>
                    </div>
                    <div class="tw:h-[30px]">
                      <Separator type="vertical" />
                    </div>
                  </template>

                  <ImageStudioChip
                    v-if="targetImage"
                    :src="targetImage.image_url"
                    @click="handleRemoveTargetImage"
                  />

                  <ImageStudioChip
                    v-for="image in referenceImages"
                    :src="image"
                    @click="handleRemoveReferenceImage(image)"
                  />
                </div>

                <!-- Prompt -->
                <FieldBaseTextarea
                  v-model="prompt"
                  :placeholder="$t('image-studio.prompt-placeholder')"
                  speechRecognition
                />

                <!-- Error -->
                <Alert v-if="generalErrorMessage" type="error">
                  {{ generalErrorMessage }}
                </Alert>

                <!-- Footer -->
                <div
                  class="tw:flex tw:flex-col tw:justify-between tw:gap-6 tw:lg:flex-row"
                >
                  <!-- Tools -->
                  <div
                    v-if="
                      enableAddReference ||
                      enableVariations ||
                      enableExpandZoom ||
                      enablePhotographicEffects ||
                      enableStyle ||
                      enableProductAttachment
                    "
                    class="tw:flex tw:items-center tw:gap-3.5"
                  >
                    <!-- Add reference button -->
                    <template v-if="enableAddReference">
                      <Tooltip
                        :disabled="
                          referenceImages.length <
                          IMAGE_STUDIO_MAX_REFERENCE_IMAGES
                        "
                        placement="top"
                        :maxWidth="178"
                      >
                        <Button
                          variant="text"
                          color="secondary"
                          leftIcon="tabler:plus"
                          size="md"
                          :disabled="
                            referenceImages.length >=
                            IMAGE_STUDIO_MAX_REFERENCE_IMAGES
                          "
                          @click="handleOpenLibrary"
                        >
                          {{ $t("image-studio.upload-to-reference") }}
                        </Button>

                        <template #content>
                          {{
                            $t("image-studio.max-references-reached", {
                              max: IMAGE_STUDIO_MAX_REFERENCE_IMAGES,
                            })
                          }}
                        </template>
                      </Tooltip>

                      <div class="tw:h-5 tw:last:hidden">
                        <Separator type="vertical" />
                      </div>
                    </template>

                    <!-- Variations dropdown -->
                    <template v-if="enableVariations">
                      <ButtonDropdown
                        placement="top"
                        variant="text"
                        color="secondary"
                        :leftIcon="VARIATIONS_STACK_ICONS[variations]"
                        size="md"
                      >
                        {{
                          $t("image-studio.variation-count", {
                            count: variations,
                          })
                        }}

                        <template #options="{ close }">
                          <ButtonDropdownOption
                            v-for="count in VARIATIONS_MAX"
                            :key="count"
                            :leftIcon="VARIATIONS_STACK_ICONS[count]"
                            :selected="variations === count"
                            @click="handleSelectVariationCount(count, close)"
                          >
                            {{
                              $t("image-studio.variation-count", {
                                count,
                              })
                            }}
                          </ButtonDropdownOption>
                        </template>
                      </ButtonDropdown>

                      <div class="tw:h-5 tw:last:hidden">
                        <Separator type="vertical" />
                      </div>
                    </template>

                    <!-- Expand / Zoom image -->
                    <template v-if="enableExpandZoom">
                      <ImageStudioExpandZoomDropdown v-model="expandZoom" />

                      <div class="tw:h-5 tw:last:hidden">
                        <Separator type="vertical" />
                      </div>
                    </template>

                    <!-- Photographic effects button -->
                    <template v-if="enablePhotographicEffects">
                      <ImageStudioChip
                        v-if="photographyEffect"
                        :src="photographyEffect.image_url"
                        @click="handleRemovePhotographicEffect()"
                        @clickImage="handleOpenPhotographyEffects"
                      >
                        {{
                          $t(
                            `image-studio.photographic-effects.${photographyEffect.name}.title`,
                          )
                        }}
                      </ImageStudioChip>
                      <Button
                        v-else
                        variant="text"
                        color="secondary"
                        leftIcon="tabler:plus"
                        size="md"
                        @click="handleOpenPhotographyEffects"
                      >
                        {{ $t("image-studio.add-photographic-effects") }}
                      </Button>

                      <div class="tw:h-5 tw:last:hidden">
                        <Separator type="vertical" />
                      </div>
                    </template>

                    <!-- Visual style button -->
                    <template v-if="enableStyle">
                      <ImageStudioChip
                        v-if="visualStyle"
                        :src="visualStyle.image ?? visualStyle.image_url"
                        @click="handleRemoveVisualStyle()"
                        @clickImage="handleOpenVisualStyles"
                      />
                      <Button
                        v-else
                        variant="text"
                        color="secondary"
                        leftIcon="tabler:plus"
                        size="md"
                        @click="handleOpenVisualStyles"
                      >
                        {{ $t("image-studio.add-style") }}
                      </Button>

                      <div class="tw:h-5 tw:last:hidden">
                        <Separator type="vertical" />
                      </div>
                    </template>

                    <!-- Add product button -->
                    <template v-if="enableProductAttachment">
                      <ImageStudioChip
                        v-if="targetProduct"
                        :src="targetProduct.thumbnail_url"
                        style="max-width: 151px"
                        @click="handleRemoveProduct()"
                        @clickImage="handleAddProduct"
                      >
                        {{ targetProduct.name }}
                      </ImageStudioChip>
                      <Button
                        v-else
                        variant="text"
                        color="secondary"
                        leftIcon="tabler:plus"
                        size="md"
                        @click="handleAddProduct"
                      >
                        {{ $t("image-studio.add-product") }}
                      </Button>

                      <div class="tw:h-5 tw:last:hidden">
                        <Separator type="vertical" />
                      </div>
                    </template>
                  </div>

                  <Button
                    type="button"
                    leftIcon="custom:hi-luca"
                    :disabled="isGenerateButtonDisabled"
                    :isLoading="isGenerating"
                    @click="handleGenerate"
                  >
                    {{ $t("image-studio.generate-image") }}
                  </Button>
                </div>
              </div>
            </CardBase>
          </Container>
        </div>
      </template>
    </GenericSubLayout>

    <!-- Unsaved changes alert -->
    <ModalFormSaveAlert :isDirty="isDirty" />

    <!-- Image Library Modal -->
    <ImageLibraryModal v-if="isLibraryOpen" v-model="isLibraryOpen" cropper />

    <!-- Photographic Effects Modal -->
    <ImageStudioPhotographicEffectsModal
      v-if="arePhotographicEffectsOpen"
      v-model="arePhotographicEffectsOpen"
      :initialSelected="photographyEffect"
      @select="handleSelectPhotographyEffect"
    />

    <!-- Visual Styles Modal -->
    <ImageStudioVisualStylesModal
      v-if="areVisualStylesOpen"
      v-model="areVisualStylesOpen"
      :customStyles="createdVisualStyles"
      :initialSelected="visualStyle"
      @select="handleSelectVisualStyle"
      @create="handleCreateVisualStyle"
    />

    <!-- Products modal -->
    <ImageStudioProductModal
      v-if="enableProductAttachment && brandId && isProductsModalOpen"
      :brandId="brandId"
      v-model="isProductsModalOpen"
      :initialProductId="targetProduct?.id"
      @select="handleSelectProduct"
    />

    <!-- Delete confirmation modal -->
    <ModalDelete
      v-if="pendingImageToDelete"
      v-model="isDeleteModalOpen"
      :confirmFn="handleConfirmDelete"
      :imgSrc="pendingImageToDelete.image_url"
    >
      <template #title>
        {{ $t("image-studio.delete-image.title") }}
      </template>

      <template #warning>
        {{ $t("image-studio.delete-image.warning") }}
      </template>
    </ModalDelete>

    <!-- Preview image -->
    <ImageStudioImagePreviewModal
      v-if="imagePreview"
      v-model="isPreviewModalOpen"
      :image="imagePreview"
      :readOnly="readOnly"
      :enableEditing="enableEditing"
      @edit="handleEditImage(imagePreview)"
      @delete="handleDeleteImage(imagePreview)"
    />

    <!-- Improve results help -->
    <ImageStudioImproveResultsModal v-model="isImproveResultsModalOpen" />
  </FullScreenOverlay>
</template>
