<script lang="ts">
import type { BrandSource } from "@/services/NewBrandsApi";

export interface BrandFormLogo {
  id: number;
  category: BrandFormLogoCategory;
  image_id?: string;
  image?: File | string;
  description: string;
  source?: BrandSource[];
  category_alias?: string | null;
}
</script>

<script setup lang="ts">
import NewBrandsApi, {
  BrandFormLogoCategory,
  type BrandLogo,
} from "@/services/NewBrandsApi";

const store = useBrandFormStore();
const notificationStore = useNotificationStore();
const { t } = useI18n();

function getInitialLogos(): BrandFormLogo[] {
  const logos = Array.isArray(store.brand.logos)
    ? store.brand.logos
    : store.brand.logos.values;

  return logos.map((apiLogo, index) => ({
    id: index,
    category: apiLogo.category,
    description: apiLogo.description,
    image_id: apiLogo.image_id ?? undefined,
    image: apiLogo.image_url ?? undefined,
    source: apiLogo.source,
    category_alias: apiLogo.category_alias ?? undefined,
  }));
}

// Store logos with their API data
const logos = ref<BrandFormLogo[]>(getInitialLogos());

const isDirty = ref(false);
const isSubmitting = ref(false);
const showDeleteAlertModal = ref(false);
const showDeleteConfirmModal = ref(false);
const selectedLogoToDelete = ref<BrandFormLogo | undefined>(undefined);

const editedLogo = ref<BrandFormLogo | undefined>(undefined);
const isCreatingModalOpen = ref(false);
const isEditModalOpen = ref(false);

// Keep local logos in sync with store refetches
watch(
  () => store.brand.logos,
  () => {
    logos.value = getInitialLogos();
  },
  { deep: true },
);

const handleCreate = () => {
  isCreatingModalOpen.value = true;
  editedLogo.value = undefined;
};

const handleEdit = (logo: BrandFormLogo) => {
  isEditModalOpen.value = true;
  editedLogo.value = logo;
};

const handleDelete = (logo: BrandFormLogo) => {
  // Display warning if the user tries to delete the only main logo available
  if (logo.category === "main-logo") {
    const mainLogoCount = logos.value.filter(
      (logo) => logo.category === "main-logo",
    ).length;

    if (mainLogoCount === 1) {
      showDeleteAlertModal.value = true;
      return;
    }
  }

  selectedLogoToDelete.value = logo;
  showDeleteConfirmModal.value = true;
};

const handleConfirmDelete = () => {
  if (!selectedLogoToDelete.value) {
    return;
  }

  const logo = selectedLogoToDelete.value;
  logos.value = logos.value.filter((_logo) => _logo.id !== logo.id);
  isDirty.value = true;

  selectedLogoToDelete.value = undefined;
};

const handleSuccessCreate = (logo: BrandFormLogo) => {
  logos.value.push(logo);
  isDirty.value = true;
};

const handleSuccessEdit = (logo: BrandFormLogo) => {
  logos.value = logos.value.map((_logo) =>
    _logo.id === logo.id ? logo : _logo,
  );
  isDirty.value = true;
};

const handleSave = async (showSuccessMessage = true) => {
  try {
    isSubmitting.value = true;

    // Upload images or get original IDs and URLs
    const images = await Promise.all(
      logos.value.map(async (logo) => {
        if (typeof logo.image === "string") {
          // If image is a string (URL from backend), keep it

          if (logo.image_id === undefined) {
            throw new Error("image_id is not defined");
          }

          return {
            image_id: logo.image_id,
            image_url: logo.image,
          };
        } else if (logo.image instanceof File) {
          // Upload new image
          const { data } = await NewBrandsApi.uploadBrandLogo(
            store.brandId,
            logo.image,
          );

          return data;
        } else {
          // No image - return null values
          return {
            image_id: null,
            image_url: null,
          };
        }
      }),
    );

    // Convert logos to API format
    const apiLogos = logos.value.map<BrandLogo>((logo, index) => ({
      id: index,
      image_id: images[index].image_id,
      image_url: images[index].image_url,
      category: logo.category,
      description: logo.description,
      source: logo.source || [],
      category_alias: logo.category_alias ?? null,
    }));

    // Save logos
    await NewBrandsApi.update(store.brandId, {
      logos: apiLogos,
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
  } catch (e: unknown) {
    console.error(e);
    // Error handling
  } finally {
    isSubmitting.value = false;
  }
};

async function handleSaveAndExit() {
  await handleSave(false);
}

async function handleBeforeUpload() {
  await await handleSave(false);
}

async function handleAfterUpload() {
  await store.refetch();
  logos.value = getInitialLogos();
}
</script>

<template>
  <BrandFormTabLayout>
    <div class="tw:flex tw:flex-col tw:justify-between tw:gap-2 tw:md:flex-row">
      <PageTitle>{{ $t("brands.settings.logos.title") }}</PageTitle>

      <Button
        variant="outlined"
        color="secondary"
        left-icon="tabler-plus"
        size="md"
        type="button"
        @click="handleCreate"
      >
        {{ $t("brands.settings.logos.add-logo") }}
      </Button>
    </div>

    <!-- Grid of logo cards -->
    <div
      v-if="logos.length > 0"
      class="tw:grid tw:gap-x-4 tw:gap-y-6 tw:md:grid-cols-2 tw:lg:grid-cols-3"
    >
      <BrandFormTabLogosLogoCard
        v-for="logo in logos"
        :logo="logo"
        @edit="handleEdit"
        @delete="handleDelete"
      />
    </div>
    <p v-else class="tw:text-sm tw:text-gray-500">
      {{ $t("brands.settings.overview.logos.empty-state") }}
    </p>

    <template #actions>
      <BrandFormGoToWorkspaceButton />

      <Button
        @click="handleSave"
        :disabled="!isDirty"
        :isLoading="isSubmitting"
        type="button"
      >
        {{ $t("brands.settings.logos.save-changes") }}
      </Button>
    </template>
  </BrandFormTabLayout>

  <!-- Modal to add a logo -->
  <BrandFormAddMethodModal
    v-if="isCreatingModalOpen"
    v-model="isCreatingModalOpen"
    section="logos"
    :loaderInterval="BRAND_NEW_CONTEXT_RING_LOADER_INTERVAL_MS"
    :loaderSteps="[
      $t('brands.settings.context-modal.logos.loader-steps.0'),
      $t('brands.settings.context-modal.logos.loader-steps.1'),
      $t('brands.settings.context-modal.logos.loader-steps.2'),
    ]"
    :beforeSubmitFn="handleBeforeUpload"
    :afterSubmitFn="handleAfterUpload"
  >
    <BrandFormTabLogosModal
      v-model="isCreatingModalOpen"
      @create="handleSuccessCreate"
    />

    <template #title>
      {{ $t("brands.settings.context-modal.logos.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.context-modal.logos.description") }}
    </template>

    <template #uploadCardDescription>
      {{ $t("brands.settings.context-modal.logos.upload-card-description") }}
    </template>

    <template #manualCardDescription>
      {{ $t("brands.settings.context-modal.logos.manual-card-description") }}
    </template>

    <template #uploadDescription>
      {{ $t("brands.settings.context-modal.logos.upload-modal-description") }}
    </template>

    <template #uploadWarning>
      {{ $t("brands.settings.context-modal.logos.upload-modal-warning") }}
    </template>
  </BrandFormAddMethodModal>

  <!-- Modal to edit a logo -->
  <BrandFormTabLogosModal
    v-if="isEditModalOpen"
    v-model="isEditModalOpen"
    :initialValues="editedLogo ?? undefined"
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
      {{ $t("brands.settings.delete-confirm.logo.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.delete-confirm.logo.description") }}
    </template>
  </ModalDelete>

  <!-- Delete warning -->
  <BrandFormDeleteAlertModal v-model="showDeleteAlertModal" type="logos">
    <template #title>
      {{ $t("brands.settings.delete-constraint.logo.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.delete-constraint.logo.description") }}
    </template>
  </BrandFormDeleteAlertModal>
</template>
