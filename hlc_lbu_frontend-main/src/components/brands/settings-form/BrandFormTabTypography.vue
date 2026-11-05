<script lang="ts">
export interface BrandFormTypographyFont {
  id?: number;
  style: BrandFormTypographyStyle;
  file?: File | string;
  file_id?: string;
  usage: BrandFormTypographyUsage;
}

export interface BrandFormTypography {
  id: number;
  fontFamily: string;
  fonts: BrandFormTypographyFont[];
}
</script>

<script setup lang="ts">
import NewBrandsApi, {
  BrandFormTypographyStyle,
  BrandFormTypographyUsage,
  type BrandTypography,
} from "@/services/NewBrandsApi";

const store = useBrandFormStore();
const notificationStore = useNotificationStore();
const { t } = useI18n();

function getInitialTypographies(): BrandFormTypography[] {
  const typographies = Array.isArray(store.brand.typography)
    ? store.brand.typography
    : store.brand.typography.values;

  return typographies.map((typography, index) => ({
    id: index,
    fontFamily: typography.family,
    fonts: typography.fonts.map((font, fontIndex) => ({
      id: font.id ?? fontIndex,
      style: font.style,
      usage: font.usage,
      file: font.file ?? undefined,
      file_id: font.file_id ?? undefined,
    })),
  }));
}

// Store typographies with their API data
const typographies = ref<BrandFormTypography[]>(getInitialTypographies());

const isDirty = ref(false);
const isSubmitting = ref(false);
const showDeleteAlertModal = ref(false);
const showDeleteConfirmModal = ref(false);
const selectedFontToDelete = ref<
  { typographyId: number; fontIndex: number } | undefined
>(undefined);

const editedTypography = ref<BrandFormTypography | undefined>();
const isCreatingModalOpen = ref(false);
const isEditModalOpen = ref(false);

// Keep local typographies in sync with store refetches
watch(
  () => store.brand.typography,
  () => {
    typographies.value = getInitialTypographies();
  },
  { deep: true },
);

const handleSuccessCreate = (typography: BrandFormTypography) => {
  typographies.value.push(typography);
  isDirty.value = true;
};

const handleSuccessEdit = (typography: BrandFormTypography) => {
  typographies.value = typographies.value.map((_typography) =>
    _typography.id === typography.id ? typography : _typography,
  );
  isDirty.value = true;
};

const handleCreate = () => {
  isCreatingModalOpen.value = true;
  editedTypography.value = undefined;
};

const handleEdit = (typography: BrandFormTypography) => {
  isEditModalOpen.value = true;
  editedTypography.value = typography;
};

const handleDelete = (typography: BrandFormTypography, fontIndex: number) => {
  // Display warning if the user tries to delete the only typography available
  if (typography.fonts.length === 1 && typographies.value.length === 1) {
    showDeleteAlertModal.value = true;
    return;
  }

  selectedFontToDelete.value = {
    typographyId: typography.id,
    fontIndex,
  };
  showDeleteConfirmModal.value = true;
};

const handleConfirmDelete = () => {
  if (!selectedFontToDelete.value) {
    return;
  }

  const selectedTypography = typographies.value.find(
    (typography) => typography.id === selectedFontToDelete.value?.typographyId,
  );

  if (!selectedTypography) {
    selectedFontToDelete.value = undefined;
    return;
  }

  const isDeletingLastFont = selectedTypography.fonts.length === 1;

  if (isDeletingLastFont) {
    // Delete the whole typography
    typographies.value = typographies.value.filter(
      (typography) => typography.id !== selectedTypography.id,
    );
  } else {
    // Delete a single font inside the typography
    typographies.value = typographies.value.map((typography) => {
      if (typography.id !== selectedTypography.id) {
        return typography;
      }

      return {
        ...typography,
        fonts: typography.fonts.filter(
          (_, index) => index !== selectedFontToDelete.value?.fontIndex,
        ),
      };
    });
  }

  isDirty.value = true;
  selectedFontToDelete.value = undefined;
};

const handleSave = async (showSuccessMessage = true) => {
  try {
    isSubmitting.value = true;

    // Process each typography family
    const apiTypographies: BrandTypography[] = await Promise.all(
      typographies.value.map(async (typography, index) => {
        // Upload font files or get original file data
        const fontFiles = await Promise.all(
          typography.fonts.map(async (font) => {
            if (typeof font.file === "string") {
              // If file is a string (filename from backend), keep it
              if (font.file_id === undefined) {
                throw new Error("file_id is not defined");
              }

              return {
                file: font.file,
                file_id: font.file_id,
              };
            } else if (font.file) {
              // Upload new image
              const { data } = await NewBrandsApi.uploadFontFile(
                store.brandId,
                font.file,
              );
              return data;
            } else {
              // No image - return null values
              return {
                file: null,
                file_id: null,
              };
            }
          }),
        );

        // Convert to API format
        return {
          id: index,
          family: typography.fontFamily,
          fonts: typography.fonts.map((font, fontIndex) => ({
            id: fontIndex,
            style: font.style,
            usage: font.usage,
            file: fontFiles[fontIndex].file,
            file_id: fontFiles[fontIndex].file_id,
          })),
        };
      }),
    );

    // Save typographies
    await NewBrandsApi.update(store.brandId, {
      typography: apiTypographies,
    });

    // Refetch the whole brand
    await store.refetch();

    if (showSuccessMessage) {
      notificationStore.display({
        type: "success",
        title: t("brands.settings.assets-updated-toast.title"),
        description: t("brands.settings.assets-updated-toast.description"),
      });
    }

    isDirty.value = false;
  } catch (e) {
    // Error handling
    console.error(e);
  } finally {
    isSubmitting.value = false;
  }
};

async function handleSaveAndExit() {
  await handleSave(false);
}

async function handleBeforeUpload() {
  await handleSave(false);
}

async function handleAfterUpload() {
  await store.refetch();
  typographies.value = getInitialTypographies();
}
</script>

<template>
  <BrandFormTabLayout>
    <div class="tw:flex tw:flex-col tw:justify-between tw:gap-2 tw:md:flex-row">
      <PageTitle>{{ $t("brands.settings.typography.title") }}</PageTitle>

      <Button
        variant="outlined"
        color="secondary"
        left-icon="tabler-plus"
        size="md"
        type="button"
        @click="handleCreate"
      >
        {{ $t("brands.settings.typography.add-font") }}
      </Button>
    </div>

    <div v-if="typographies.length > 0" class="tw:grid tw:gap-4">
      <div
        v-for="typography in typographies"
        class="tw:grid tw:gap-4 tw:lg:grid-cols-5"
      >
        <BrandFormTabTypographyCard
          :typography="typography"
          @edit="handleEdit"
          @delete="handleDelete"
        />
      </div>
    </div>
    <p v-else class="tw:text-sm tw:text-gray-500">
      {{ $t("brands.settings.typography.no-fonts-added") }}
    </p>

    <template #actions>
      <BrandFormGoToWorkspaceButton />

      <Button
        @click="handleSave"
        :disabled="!isDirty"
        :isLoading="isSubmitting"
        type="button"
      >
        {{ $t("brands.settings.typography.save-changes") }}
      </Button>
    </template>
  </BrandFormTabLayout>

  <!-- Modal to add typography -->
  <BrandFormAddMethodModal
    v-if="isCreatingModalOpen"
    v-model="isCreatingModalOpen"
    section="typography"
    :loaderInterval="BRAND_NEW_CONTEXT_RING_LOADER_INTERVAL_MS"
    :loaderSteps="[
      $t('brands.settings.context-modal.typography.loader-steps.0'),
      $t('brands.settings.context-modal.typography.loader-steps.1'),
      $t('brands.settings.context-modal.typography.loader-steps.2'),
    ]"
    :beforeSubmitFn="handleBeforeUpload"
    :afterSubmitFn="handleAfterUpload"
  >
    <BrandFormTabTypographyModal
      v-model="isCreatingModalOpen"
      @create="handleSuccessCreate"
    />

    <template #title>
      {{ $t("brands.settings.context-modal.typography.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.context-modal.typography.description") }}
    </template>

    <template #uploadCardDescription>
      {{
        $t("brands.settings.context-modal.typography.upload-card-description")
      }}
    </template>

    <template #manualCardDescription>
      {{
        $t("brands.settings.context-modal.typography.manual-card-description")
      }}
    </template>

    <template #uploadDescription>
      {{
        $t("brands.settings.context-modal.typography.upload-modal-description")
      }}
    </template>

    <template #uploadWarning>
      {{ $t("brands.settings.context-modal.typography.upload-modal-warning") }}
    </template>
  </BrandFormAddMethodModal>

  <!-- Modal to edit typography -->
  <BrandFormTabTypographyModal
    v-if="isEditModalOpen"
    v-model="isEditModalOpen"
    :initialValues="editedTypography ?? undefined"
    @edit="handleSuccessEdit"
  />

  <!-- Save locking -->
  <ModalFormSaveOrDiscard :isDirty="isDirty" :saveFn="handleSaveAndExit" />

  <!-- Delete confirmation -->
  <ModalDelete
    v-model="showDeleteConfirmModal"
    :confirmFn="handleConfirmDelete"
  >
    <template #title>
      {{ $t("brands.settings.delete-confirm.typography.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.delete-confirm.typography.description") }}
    </template>
  </ModalDelete>

  <!-- Delete warning -->
  <BrandFormDeleteAlertModal v-model="showDeleteAlertModal" type="typography">
    <template #title>
      {{ $t("brands.settings.delete-constraint.typography.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.delete-constraint.typography.description") }}
    </template>
  </BrandFormDeleteAlertModal>
</template>
