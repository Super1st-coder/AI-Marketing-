<script setup lang="ts">
import ProductsApi, { ProductImage } from "@/services/ProductsApi.ts";
import { ProductFormData } from "./ProductForm.vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

const brandId = useBrandId();
const imageLibraryStore = useImageLibraryStore();
const notificationStore = useNotificationStore();

const { goNext, goBack, data, saveData } =
  useMultiStepFormContext<ProductFormData>();

const isOpen = ref(false);
const isHelpfulDetailsModalOpen = ref(false);
const libraryTargetId = ref(Symbol("ImageLibraryModal"));
const uploadingImages = ref(0);

const isDeleteModalOpen = ref(false);
const pendingImageToDelete = ref<ProductImage>();

const images = computed(() => [...(data.value.images ?? [])].reverse());
const imagesCount = computed<number>(() =>
  data.value.locked
    ? (data.value.images?.length ?? 0)
    : PRODUCT_IMAGE_SLOT_COUNT,
);

const isValid = computed(() => images.value.length > 0);
const isLoading = computed(() => uploadingImages.value > 0);
const generalErrorMessage = ref<string>();

function onSubmit() {
  generalErrorMessage.value = undefined;

  if (data.value?.locked) {
    goNext({ isDirty: false });
    return;
  }

  if (!isValid.value) {
    generalErrorMessage.value = t("products.image.at-least-one-image");
    return;
  }

  goNext();
}

function handleOpenLibrary() {
  imageLibraryStore.setActiveTarget(libraryTargetId.value);
  isOpen.value = true;
}

async function handleFileUploaded(image: ImageLibraryFile) {
  // Close library
  isOpen.value = false;
  uploadingImages.value = uploadingImages.value + 1;

  try {
    const productId = data.value.id;
    if (!(image instanceof File)) return;

    if (image.raw) {
      await ProductsApi.uploadImage(brandId, productId, image);
    } else {
      await ProductsApi.uploadImageFromImgLibrary(
        brandId,
        productId,
        image.libraryId,
      );
    }

    const { data: product } = await ProductsApi.getOne(brandId, productId);

    saveData({
      ...product,
    });
    generalErrorMessage.value = undefined;
  } catch (error: any) {
    if (error?.message?.code === "PROD02") {
      notificationStore.display({
        type: "warning",
        title: t("products.image.already-uploaded-toast.title"),
        description: t("products.image.already-uploaded-toast.description"),
      });
    } else {
      notificationStore.display({
        type: "warning",
        title: t("products.image.upload-error-toast.title"),
        description: t("products.image.upload-error-toast.description"),
      });
    }
  } finally {
    uploadingImages.value = uploadingImages.value - 1;
  }
}

function handleDeleteImage(image?: ProductImage) {
  if (!image) return;

  pendingImageToDelete.value = image;
  isDeleteModalOpen.value = true;
}

async function handleConfirmDelete() {
  if (!pendingImageToDelete.value) return;

  try {
    const productId = data.value.id;

    await ProductsApi.deleteImage(
      brandId,
      productId,
      pendingImageToDelete.value.thumbnail_id,
    );

    const { data: product } = await ProductsApi.getOne(brandId, productId);

    saveData({
      ...product,
    });
  } catch (error: any) {
    console.error("Failed to delete product image:", error);

    notificationStore.display({
      type: "warning",
      title: t("products.image.delete-error-toast.title"),
      description: t("products.image.delete-error-toast.description"),
    });
  } finally {
    pendingImageToDelete.value = undefined;
  }
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
      await handleFileUploaded(file);
    }
  },
);
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :maxWidth="1100">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=JV82EPwpUUw"
    >
      {{ t("products.image.title") }}

      <template #description>
        {{ t("products.image.description") }}
      </template>
    </PageTitle>

    <CardBase borderRadius="md" class="tw:grid tw:grid-cols-1 tw:gap-5 tw:p-6">
      <h2 class="tw:text-xl tw:font-bold">
        {{ t("products.image.upload-heading") }}
      </h2>

      <Alert type="info">
        <i18n-t
          keypath="products.image.optimization-tip"
          tag="span"
          class="tw:block tw:lg:mr-14"
        >
          <template #label>
            <strong>{{ t("products.image.optimization-tip-label") }}</strong>
          </template>
          <template #addImage>
            <strong>{{ t("products.image.add-image-option") }}</strong>
          </template>
        </i18n-t>

        <template #actions>
          <Link
            is="button"
            underline
            class="tw:whitespace-nowrap"
            color="info-dark"
            @click="isHelpfulDetailsModalOpen = true"
          >
            {{ t("products.image.guide-of-helpful-details") }}
          </Link>
        </template>
      </Alert>

      <div
        class="tw:grid tw:grid-cols-1 tw:gap-4 tw:md:grid-cols-2 tw:xl:grid-cols-5"
      >
        <ProductFormImageSlot
          v-for="slot in imagesCount"
          :image="images?.[slot - 1]?.url"
          :isSaving="
            uploadingImages
              ? slot >= images.length + 1 &&
                slot <= images.length + uploadingImages
              : false
          "
          :readOnly="data.locked"
          @add="handleOpenLibrary"
          @delete="handleDeleteImage(images?.[slot - 1])"
        />
      </div>

      <Alert v-if="generalErrorMessage" type="error" autoScroll>
        {{ generalErrorMessage }}
      </Alert>
    </CardBase>

    <ImageLibraryModal v-model="isOpen" cropper />

    <ProductFormImageHelpfulDetailsModal v-model="isHelpfulDetailsModalOpen" />

    <!-- Delete confirmation modal -->
    <ModalDelete
      v-if="pendingImageToDelete"
      v-model="isDeleteModalOpen"
      :confirmFn="handleConfirmDelete"
      :imgSrc="pendingImageToDelete.url"
    >
      <template #title>
        {{ t("products.image.delete.title") }}
      </template>

      <template #warning>
        {{ t("products.image.delete.warning") }}
      </template>
    </ModalDelete>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" type="button" />
        <ButtonNext :isLoading="isLoading" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
