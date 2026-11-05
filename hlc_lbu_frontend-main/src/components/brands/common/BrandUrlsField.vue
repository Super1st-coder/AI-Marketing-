<script setup lang="ts">
import type { DeleteBackendFileConfirmFn } from "@/components/forms/base/FieldFiles.vue";
import type { BrandSavedDataSource } from "./BrandFilesAndUrlsTabs.vue";

const props = defineProps<{
  disabled?: boolean;
  deleteBackendUrlConfirmFn?: DeleteBackendFileConfirmFn<BrandSavedDataSource>;
}>();

type UrlRow = string | BrandSavedDataSource;

const urls = useFieldArray<UrlRow | undefined>("urls");

const showDeleteConfirmModal = ref(false);
const backendUrlIndexToDelete = ref(0);

function isBackendUrl(item: UrlRow): item is BrandSavedDataSource {
  return item !== undefined && typeof item === "object";
}

const backendUrlToDelete = computed<BrandSavedDataSource | undefined>(() => {
  const value = urls.fields.value[backendUrlIndexToDelete.value]?.value;
  return value !== undefined && isBackendUrl(value) ? value : undefined;
});

function addUrl() {
  urls.push(undefined);
}

function removeUrlAt(index: number) {
  urls.remove(index);
}

function handleRemoveClick(index: number) {
  const url = urls.fields.value[index].value;

  if (url === undefined || !isBackendUrl(url)) {
    removeUrlAt(index);
    return;
  }

  if (!props.deleteBackendUrlConfirmFn) {
    return;
  }

  backendUrlIndexToDelete.value = index;
  showDeleteConfirmModal.value = true;
}

async function handleConfirmBackendDelete() {
  if (!props.deleteBackendUrlConfirmFn || !backendUrlToDelete.value) {
    return;
  }

  await props.deleteBackendUrlConfirmFn(backendUrlToDelete.value);
  removeUrlAt(backendUrlIndexToDelete.value);
}
</script>

<template>
  <div class="tw:grid tw:grid-cols-1 tw:gap-6">
    <div
      v-for="(field, index) in urls.fields.value"
      :key="field.key"
      class="tw:flex tw:items-start tw:gap-2"
    >
      <div class="tw:grow">
        <!-- Back-end URL -->
        <FieldText
          v-if="field.value !== undefined && isBackendUrl(field.value)"
          :name="`urls[${index}].name`"
          :placeholder="$t('brands.create.upload-modal.url.placeholder')"
          leftIcon="solar:link-bold"
          disabled
        />
        <!-- Client URL -->
        <FieldText
          v-else
          :name="`urls[${index}]`"
          :placeholder="$t('brands.create.upload-modal.url.placeholder')"
          leftIcon="solar:link-bold"
          :disabled="disabled"
        />
      </div>

      <Button
        type="button"
        variant="outlined"
        color="secondary"
        icon="tabler-x"
        :disabled="disabled"
        @click="handleRemoveClick(index)"
      />
    </div>

    <div>
      <Button
        type="button"
        variant="outlined"
        color="secondary"
        leftIcon="tabler:plus"
        size="md"
        :disabled="disabled"
        @click="addUrl"
      >
        URLs
      </Button>
    </div>

    <ModalDelete
      v-if="deleteBackendUrlConfirmFn !== undefined && backendUrlToDelete"
      v-model="showDeleteConfirmModal"
      :confirmFn="handleConfirmBackendDelete"
    >
      <template #title>
        {{ $t("brands.create.upload-modal.files.delete-data-source-title") }}
      </template>

      <template #description>
        {{
          $t(
            "brands.create.upload-modal.files.delete-data-source-description",
            { nameFileOrUrl: backendUrlToDelete.name },
          )
        }}
      </template>

      <template #warning>
        {{ $t("brands.create.upload-modal.files.delete-data-source-warning") }}
      </template>
    </ModalDelete>
  </div>
</template>
