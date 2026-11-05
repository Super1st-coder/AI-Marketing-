<script lang="ts">
import NewBrandsApi, {
  type BrandFormRuleType,
  type BrandDosDont,
  type BrandSource,
} from "@/services/NewBrandsApi";

export interface BrandFormRule {
  id: number;
  type: BrandFormRuleType;
  text: string;
  image_id?: string;
  image?: File | string;
  source?: BrandSource[];
}
</script>

<script setup lang="ts">
const store = useBrandFormStore();
const notificationStore = useNotificationStore();
const { t } = useI18n();

const editedRule = ref<BrandFormRule | undefined>();
const isCreatingModalOpen = ref(false);
const isEditModalOpen = ref(false);
const isDirty = ref(false);
const isSubmitting = ref(false);
const showDeleteConfirmModal = ref(false);
const selectedRuleToDelete = ref<BrandFormRule | undefined>(undefined);

function getInitialRules(): BrandFormRule[] {
  return store.brand.dos_donts.map((apiRule, index) => ({
    id: index,
    type: apiRule.type,
    text: apiRule.rule,
    image_id: apiRule.image_id ?? undefined,
    image: apiRule.image_url ?? undefined,
    source: apiRule.source,
  }));
}

// Store rules with their API data
const rules = ref<BrandFormRule[]>(getInitialRules());

// Keep local rules in sync with store refetches
watch(
  () => store.brand.dos_donts,
  () => {
    rules.value = getInitialRules();
  },
  { deep: true },
);

const dosRules = computed(() =>
  rules.value.filter((rule) => rule.type === "do"),
);

const dontsRules = computed(() =>
  rules.value.filter((rule) => rule.type === "dont"),
);

const handleSuccessCreate = (rule: BrandFormRule) => {
  rules.value.push(rule);
  isDirty.value = true;
};

const handleSuccessEdit = (rule: BrandFormRule) => {
  rules.value = rules.value.map((_rule) =>
    _rule.id === rule.id ? rule : _rule,
  );
  isDirty.value = true;
};

const handleCreate = () => {
  isCreatingModalOpen.value = true;
  editedRule.value = undefined;
};

const handleEdit = (rule: BrandFormRule) => {
  isEditModalOpen.value = true;
  editedRule.value = rule;
};

const handleDelete = (rule: BrandFormRule) => {
  selectedRuleToDelete.value = rule;
  showDeleteConfirmModal.value = true;
};

const handleConfirmDelete = () => {
  if (!selectedRuleToDelete.value) {
    return;
  }

  const rule = selectedRuleToDelete.value;
  rules.value = rules.value.filter((_rule) => _rule.id !== rule.id);
  isDirty.value = true;

  selectedRuleToDelete.value = undefined;
};

const handleSave = async (showSuccessMessage = true) => {
  isSubmitting.value = true;

  try {
    // Upload images or get original IDs and URLs
    const images = await Promise.all(
      rules.value.map(async (rule) => {
        if (typeof rule.image === "string") {
          // If image is a string (URL from backend), keep it
          if (rule.image_id === undefined) {
            throw new Error("image_id is not defined");
          }

          return {
            image_id: rule.image_id,
            image_url: rule.image,
          };
        } else if (rule.image instanceof File) {
          // Upload new image
          const { data } = await NewBrandsApi.uploadDoDontImage(
            store.brandId,
            rule.image,
          );
          return data;
        } else {
          // No image - return empty values
          return {
            image_id: null,
            image_url: null,
          };
        }
      }),
    );

    // Convert local rules to API format
    const apiRules: BrandDosDont[] = rules.value.map((rule, index) => ({
      id: index,
      type: rule.type,
      rule: rule.text,
      image_id: images[index].image_id,
      image_url: images[index].image_url,
      source: rule.source ?? [],
    }));

    // Save
    await NewBrandsApi.update(store.brandId, {
      dos_donts: apiRules,
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
  } catch (error) {
    console.error("Error saving dos and donts:", error);
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
  rules.value = getInitialRules();
}
</script>

<template>
  <BrandFormTabLayout>
    <div class="tw:flex tw:flex-col tw:justify-between tw:gap-2 tw:md:flex-row">
      <PageTitle>{{ $t("brands.settings.dos-and-donts.title") }}</PageTitle>

      <Button
        variant="outlined"
        color="secondary"
        left-icon="tabler-plus"
        size="md"
        type="button"
        @click="handleCreate"
      >
        {{ $t("brands.settings.dos-and-donts.add-rule") }}
      </Button>
    </div>

    <div class="tw:grid tw:gap-5 tw:lg:grid-cols-2">
      <!-- Do's Section -->
      <div class="tw:flex tw:flex-col">
        <div class="tw:flex tw:items-center tw:gap-2 tw:py-3">
          <Icon
            icon="tabler:circle-check-filled"
            class="tw:text-xl tw:text-success-500"
          />
          <h2 class="tw:font-semibold">
            {{ $t("brands.settings.dos-and-donts.dos") }}
          </h2>
        </div>

        <div v-if="dosRules.length > 0" class="tw:flex tw:flex-col tw:gap-6">
          <BrandFormTabDosAndDontsCard
            v-for="rule in dosRules"
            :key="rule.id"
            :rule="rule"
            @edit="handleEdit"
            @delete="handleDelete"
          />
        </div>
        <p v-else class="tw:text-sm tw:text-gray-500">
          {{ $t("brands.settings.dos-and-donts.no-rules-added") }}
        </p>
      </div>

      <!-- Don'ts Section -->
      <div class="tw:flex tw:flex-col">
        <div class="tw:flex tw:items-center tw:gap-2 tw:py-3">
          <Icon
            icon="tabler:circle-x-filled"
            class="tw:text-xl tw:text-error-500"
          />
          <h2 class="tw:font-semibold">
            {{ $t("brands.settings.dos-and-donts.donts") }}
          </h2>
        </div>

        <div v-if="dontsRules.length > 0" class="tw:flex tw:flex-col tw:gap-6">
          <BrandFormTabDosAndDontsCard
            v-for="rule in dontsRules"
            :key="rule.id"
            :rule="rule"
            @edit="handleEdit"
            @delete="handleDelete"
          />
        </div>
        <p v-else class="tw:text-sm tw:text-gray-500">
          {{ $t("brands.settings.dos-and-donts.no-rules-added") }}
        </p>
      </div>
    </div>

    <template #actions>
      <BrandFormGoToWorkspaceButton />

      <Button
        :disabled="!isDirty"
        :isLoading="isSubmitting"
        @click="handleSave"
      >
        {{ $t("brands.settings.dos-and-donts.save-changes") }}
      </Button>
    </template>
  </BrandFormTabLayout>

  <!-- Modal to add do's and don'ts -->
  <BrandFormAddMethodModal
    v-if="isCreatingModalOpen"
    v-model="isCreatingModalOpen"
    section="dos_donts"
    :loaderInterval="BRAND_NEW_CONTEXT_RING_LOADER_INTERVAL_MS"
    :loaderSteps="[
      $t('brands.settings.context-modal.dos-and-donts.loader-steps.0'),
      $t('brands.settings.context-modal.dos-and-donts.loader-steps.1'),
      $t('brands.settings.context-modal.dos-and-donts.loader-steps.2'),
      $t('brands.settings.context-modal.dos-and-donts.loader-steps.3'),
    ]"
    :beforeSubmitFn="handleBeforeUpload"
    :afterSubmitFn="handleAfterUpload"
  >
    <BrandFormTabDosAndDontsModal
      v-model="isCreatingModalOpen"
      @create="handleSuccessCreate"
    />

    <template #title>
      {{ $t("brands.settings.context-modal.dos-and-donts.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.context-modal.dos-and-donts.description") }}
    </template>

    <template #uploadCardDescription>
      {{
        $t(
          "brands.settings.context-modal.dos-and-donts.upload-card-description",
        )
      }}
    </template>

    <template #manualCardDescription>
      {{
        $t(
          "brands.settings.context-modal.dos-and-donts.manual-card-description",
        )
      }}
    </template>

    <template #uploadDescription>
      {{
        $t(
          "brands.settings.context-modal.dos-and-donts.upload-modal-description",
        )
      }}
    </template>

    <template #uploadWarning>
      {{
        $t("brands.settings.context-modal.dos-and-donts.upload-modal-warning")
      }}
    </template>
  </BrandFormAddMethodModal>

  <!-- Modal to edit do's and don'ts -->
  <BrandFormTabDosAndDontsModal
    v-if="isEditModalOpen"
    v-model="isEditModalOpen"
    :initialValues="editedRule ?? undefined"
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
      {{ $t("brands.settings.delete-confirm.rule.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.delete-confirm.rule.description") }}
    </template>
  </ModalDelete>
</template>
