<script lang="ts" setup>
import { ImageStudioVariationImage } from "@/components/images/studio/types";
import { TargetCustomerFormData } from "../TargetCustomerForm.vue";
import BuyerPersonImagesApi, {
  BuyerPersonMainImage,
} from "@/services/BuyerPersonImagesApi";
import { UnidentifiedError } from "@/services/common-errors.ts";

const isOpen = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  success: [
    selectedFile: ImageLibraryFile,
    variants: ImageStudioVariationImage[],
    mainImage: BuyerPersonMainImage,
  ];
}>();

const { t } = useI18n();
const { data } = useMultiStepFormContext<TargetCustomerFormData>();

const imageLibraryStore = useImageLibraryStore();
const libraryTargetId = ref(Symbol("ImageLibraryModal"));

const screen = ref<"library" | "confirm" | "loader">("library");
const isReady = ref(false);
const isUploading = ref(false);
const generalErrorMessage = ref<string | undefined>(undefined);
const selectedFile = ref<ImageLibraryFile | undefined>(undefined);

const variationLoaderSteps = computed(() => [
  t("buyer-person.image.variations-loader.steps.studying-features"),
  t("buyer-person.image.variations-loader.steps.keeping-face-shape"),
  t("buyer-person.image.variations-loader.steps.creating-angles"),
  t("buyer-person.image.variations-loader.steps.finalizing-options"),
]);

onMounted(() => {
  imageLibraryStore.setActiveTarget(libraryTargetId.value);
});

function handleFileSelected(file: ImageLibraryFile) {
  selectedFile.value = file;
  screen.value = "confirm";
}

// Store the selected image from the library
watch(
  () => imageLibraryStore.selectedFile,
  async (file) => {
    if (!file) return;

    if (
      imageLibraryStore.lastTarget &&
      imageLibraryStore.lastTarget === libraryTargetId.value
    ) {
      handleFileSelected(file);
    }
  },
);

async function uploadAndSelectMainImage(
  file: ImageLibraryFile,
): Promise<BuyerPersonMainImage> {
  let uploaded: BuyerPersonMainImage;

  if (file.raw) {
    const response = await BuyerPersonImagesApi.uploadMainImageBinary({
      brand_id: data.value.brandId,
      bperson_id: data.value.id,
      file,
    });

    uploaded = response.data;
  } else {
    const response = await BuyerPersonImagesApi.uploadMainImageById({
      brand_id: data.value.brandId,
      bperson_id: data.value.id,
      image_id: file.libraryId,
    });

    uploaded = response.data;
  }

  const selected = await BuyerPersonImagesApi.selectMainImage({
    brand_id: data.value.brandId,
    bperson_id: data.value.id,
    image_id: uploaded.image_id,
  });

  return selected.data;
}

function getExploreLibraryErrorMessage(error: any) {
  const errorCode = error?.message?.code as string | undefined;

  if (errorCode === "SYSVAL001") {
    return t(
      "buyer-person.image.explore-library-modal.confirm.main-image-already-exists",
    );
  }

  return t("global.unexpected-error");
}

async function handleUploadVariants() {
  assert(selectedFile.value);
  generalErrorMessage.value = undefined;
  isUploading.value = true;

  try {
    const mainImage = await uploadAndSelectMainImage(selectedFile.value);

    emit("success", selectedFile.value, [], mainImage);
  } catch (error) {
    console.log(error);
    generalErrorMessage.value = getExploreLibraryErrorMessage(error);
    isUploading.value = false;
  } finally {
    // The success callback could take a while to complete, so we
    // don't set the isUploading flag to false to avoid flickering
  }
}

async function handleGenerateVariations() {
  assert(selectedFile.value);
  generalErrorMessage.value = undefined;

  // Loader screen
  screen.value = "loader";

  let uploadedMainImage: BuyerPersonMainImage | undefined;

  try {
    uploadedMainImage = await uploadAndSelectMainImage(selectedFile.value);

    // Start the variants generation job
    const response = await BuyerPersonImagesApi.startGenerateVariantsJob({
      brand_id: data.value.brandId,
      bperson_id: data.value.id,
      image_id: uploadedMainImage.image_id,
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

    if (result.status === "FAILED") {
      throw new UnidentifiedError();
    }

    // Fetch the generated variants
    const { variants } = (
      await BuyerPersonImagesApi.getMainImageVariants(
        data.value.brandId,
        data.value.id,
        uploadedMainImage.image_id,
      )
    ).data;

    if (variants.length === 0) {
      throw new UnidentifiedError();
    }

    // Display the last step in loader for a moment
    isReady.value = true;
    await sleep(4 * SECOND_IN_MS);

    emit(
      "success",
      selectedFile.value,
      variants.map(({ id, image_id, image_url, prompt, label }) => ({
        id,
        image_id,
        label,
        image_url,
        prompt,
      })),
      uploadedMainImage,
    );
  } catch (error) {
    console.log(error);

    if (uploadedMainImage) {
      await BuyerPersonImagesApi.deleteMainImage({
        brand_id: data.value.brandId,
        bperson_id: data.value.id,
        main_image_id: uploadedMainImage.id,
      });
    }

    generalErrorMessage.value = getExploreLibraryErrorMessage(error);

    // Go back to the previous screen
    screen.value = "confirm";
    isReady.value = false;
  } finally {
    // The success callback could take a while to complete, so we
    // don't set the screen to "confirm" to avoid flickering
  }
}
</script>

<template>
  <!-- Initial screen with selection with the image Library Modal -->
  <ImageLibraryModal v-if="screen === 'library'" v-model="isOpen" cropper />
  <!-- Modal to confirm what to do with the selected image -->
  <Modal
    v-if="screen === 'confirm'"
    v-model="isOpen"
    :maxWidth="600"
    :closeButton="!isUploading"
    :closeOnClickOutside="!isUploading"
  >
    <ModalHeader>
      {{ $t("buyer-person.image.explore-library-modal.confirm.title") }}

      <template #description>
        {{ $t("buyer-person.image.explore-library-modal.confirm.description") }}
      </template>
    </ModalHeader>

    <ModalBody class="tw:flex tw:flex-col tw:gap-5">
      <ImgFile
        :src="selectedFile"
        class="tw:mx-auto tw:mb-6 tw:rounded-2xl tw:object-contain"
        style="max-height: 400px"
      />

      <Alert v-if="generalErrorMessage" type="error">
        {{ generalErrorMessage }}
      </Alert>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        color="secondary"
        variant="outlined"
        :disabled="isUploading"
        @click="isOpen = false"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button
        type="button"
        leftIcon="tabler:upload"
        variant="label"
        color="primary"
        :isLoading="isUploading"
        @click="handleUploadVariants"
      >
        {{
          $t("buyer-person.image.explore-library-modal.confirm.upload-variants")
        }}
      </Button>

      <Button
        type="button"
        leftIcon="custom:hi-luca"
        :disabled="isUploading"
        @click="handleGenerateVariations"
      >
        {{
          $t(
            "buyer-person.image.explore-library-modal.confirm.generate-ai-variations",
          )
        }}
      </Button>
    </ModalFooter>
  </Modal>
  <!-- Ring loader -->
  <ModalRingLoader
    v-else-if="screen === 'loader'"
    v-model="isOpen"
    :isReady="isReady"
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
</template>
