<script lang="ts">
import type { BrandSource } from "@/services/NewBrandsApi";

export interface BrandFormColor {
  id: number;
  name: string;
  hex: string;
  category: BrandFormColorCategory;
  source?: BrandSource[];
}
</script>

<script setup lang="ts">
import NewBrandsApi, {
  brandFormColorCategories,
  BrandFormColorCategory,
  type BrandColor,
} from "@/services/NewBrandsApi";

const store = useBrandFormStore();
const notificationStore = useNotificationStore();
const { t } = useI18n();

function getInitialColors(): BrandFormColor[] {
  const colors = Array.isArray(store.brand.colors)
    ? store.brand.colors
    : store.brand.colors.values;

  return colors.map((apiColor, index) => ({
    id: index,
    name: apiColor.name,
    hex: apiColor.hex_code,
    category: apiColor.category,
    source: apiColor.source,
  }));
}

// Store colors with their API data
const colors = ref<BrandFormColor[]>(getInitialColors());

const isDirty = ref(false);
const isSubmitting = ref(false);
const showDeleteAlertModal = ref(false);
const showDeleteConfirmModal = ref(false);
const selectedColorToDelete = ref<BrandFormColor | undefined>(undefined);

const editedColor = ref<BrandFormColor | undefined>();
const isCreatingModalOpen = ref(false);
const isEditModalOpen = ref(false);

// Keep local colors in sync with store refetches
watch(
  () => store.brand.colors,
  () => {
    colors.value = getInitialColors();
  },
  { deep: true },
);

const colorsByCategories = computed(() => {
  const result: Partial<Record<BrandFormColorCategory, BrandFormColor[]>> = {};

  for (const category of brandFormColorCategories) {
    const _colors = colors.value.filter((color) => color.category === category);
    result[category] = _colors ?? [];
  }

  return result;
});

const handleSuccessCreate = (color: BrandFormColor) => {
  colors.value.push(color);
  isDirty.value = true;
};

const handleSuccessEdit = (color: BrandFormColor) => {
  colors.value = colors.value.map((_color) =>
    _color.id === color.id ? color : _color,
  );
  isDirty.value = true;
};

const handleCreate = () => {
  isCreatingModalOpen.value = true;
  editedColor.value = undefined;
};

const handleEdit = (color: BrandFormColor) => {
  isEditModalOpen.value = true;
  editedColor.value = color;
};

const handleDelete = (color: BrandFormColor) => {
  // Display warning if the user tries to delete the only primary color available
  if (color.category === "primary") {
    const primaryColorCount = colors.value.filter(
      (_color) => _color.category === "primary",
    ).length;

    if (primaryColorCount === 1) {
      showDeleteAlertModal.value = true;
      return;
    }
  }

  selectedColorToDelete.value = color;
  showDeleteConfirmModal.value = true;
};

const handleConfirmDelete = () => {
  if (!selectedColorToDelete.value) {
    return;
  }

  const color = selectedColorToDelete.value;
  colors.value = colors.value.filter((_color) => _color.id !== color.id);
  isDirty.value = true;

  selectedColorToDelete.value = undefined;
};

const handleSave = async (showSuccessMessage = true) => {
  try {
    isSubmitting.value = true;

    // Convert colors to API format
    const apiColors: BrandColor[] = colors.value.map((color, index) => ({
      id: index,
      name: color.name,
      hex_code: color.hex,
      category: color.category,
      source: color.source || [],
    }));

    await NewBrandsApi.update(store.brandId, {
      colors: apiColors,
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
  await handleSave(false);
}

async function handleAfterUpload() {
  await store.refetch();
  colors.value = getInitialColors();
}
</script>

<template>
  <BrandFormTabLayout>
    <div class="tw:flex tw:flex-col tw:justify-between tw:gap-2 tw:md:flex-row">
      <PageTitle>{{ $t("brands.settings.colors.title") }}</PageTitle>

      <Button
        variant="outlined"
        color="secondary"
        left-icon="tabler-plus"
        size="md"
        type="button"
        @click="handleCreate"
      >
        {{ $t("brands.settings.colors.add-color") }}
      </Button>
    </div>

    <div v-for="(colors, category) in colorsByCategories">
      <h2 class="tw:py-3 tw:font-semibold">
        {{ $t(`brands.settings.colors.categories.${category}`) }}
      </h2>

      <div
        v-if="colors && category && colors.length > 0"
        class="tw:grid tw:gap-4 tw:lg:grid-cols-5"
      >
        <BrandFormTabColorsCard
          v-for="color in colors"
          :key="color.id"
          :color="color"
          @edit="handleEdit"
          @delete="handleDelete"
        />
      </div>
      <p v-else class="tw:text-sm tw:text-gray-500">
        {{ $t(`brands.settings.colors.no-colors-added.${category}`) }}
      </p>
    </div>

    <template #actions>
      <BrandFormGoToWorkspaceButton />

      <Button
        @click="handleSave"
        :disabled="!isDirty"
        :isLoading="isSubmitting"
        type="button"
      >
        {{ $t("brands.settings.colors.save-changes") }}
      </Button>
    </template>
  </BrandFormTabLayout>

  <!-- Modal to add a color -->
  <BrandFormAddMethodModal
    v-if="isCreatingModalOpen"
    v-model="isCreatingModalOpen"
    section="colors"
    :loaderInterval="BRAND_NEW_CONTEXT_RING_LOADER_INTERVAL_MS"
    :loaderSteps="[
      $t('brands.settings.context-modal.colors.loader-steps.0'),
      $t('brands.settings.context-modal.colors.loader-steps.1'),
      $t('brands.settings.context-modal.colors.loader-steps.2'),
    ]"
    :beforeSubmitFn="handleBeforeUpload"
    :afterSubmitFn="handleAfterUpload"
  >
    <BrandFormTabColorsModal
      v-model="isCreatingModalOpen"
      @create="handleSuccessCreate"
    />

    <template #title>
      {{ $t("brands.settings.context-modal.colors.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.context-modal.colors.description") }}
    </template>

    <template #uploadCardDescription>
      {{ $t("brands.settings.context-modal.colors.upload-card-description") }}
    </template>

    <template #manualCardDescription>
      {{ $t("brands.settings.context-modal.colors.manual-card-description") }}
    </template>

    <template #uploadDescription>
      {{ $t("brands.settings.context-modal.colors.upload-modal-description") }}
    </template>

    <template #uploadWarning>
      {{ $t("brands.settings.context-modal.colors.upload-modal-warning") }}
    </template>
  </BrandFormAddMethodModal>

  <!-- Modal to edit a color -->
  <BrandFormTabColorsModal
    v-if="isEditModalOpen"
    v-model="isEditModalOpen"
    :initialValues="editedColor ?? undefined"
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
      {{ $t("brands.settings.delete-confirm.color.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.delete-confirm.color.description") }}
    </template>
  </ModalDelete>

  <!-- Delete warning -->
  <BrandFormDeleteAlertModal v-model="showDeleteAlertModal" type="colors">
    <template #title>
      {{ $t("brands.settings.delete-constraint.color.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.delete-constraint.color.description") }}
    </template>
  </BrandFormDeleteAlertModal>
</template>
