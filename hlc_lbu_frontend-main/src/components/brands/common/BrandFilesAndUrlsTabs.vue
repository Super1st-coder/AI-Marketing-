<script setup lang="ts">
import type {
  DeleteBackendFileConfirmFn,
  FieldFilesBackendFile,
} from "@/components/forms/base/FieldFiles.vue";

/** A saved file or URL of the brand, with its data source id to delete it. */
export type BrandSavedDataSource = FieldFilesBackendFile & {
  id: number;
};

defineProps<{
  disabled?: boolean;
  deleteBackendFileConfirmFn?: DeleteBackendFileConfirmFn<BrandSavedDataSource>;
  deleteBackendUrlConfirmFn?: DeleteBackendFileConfirmFn<BrandSavedDataSource>;
}>();

const currentTab = defineModel<"file" | "urls">({ default: "file" });

const errors = useFormErrors<{ files; urls }>();
const isSubmitting = useIsSubmitting();

// Switch to Files/URLs tab if there are validation errors
watch(isSubmitting, (submitting, wasSubmitting) => {
  if (!wasSubmitting || submitting) return;

  if (errors.value.files) {
    // Check errors in the file field
    currentTab.value = "file";
  } else if (Object.keys(errors.value).some((key) => key.includes("urls"))) {
    // Check if there's any error related to URLs
    currentTab.value = "urls";
  }
});
</script>

<template>
  <Tabs v-model="currentTab" keepOnUnmount>
    <template #list>
      <Tab value="file" disableSaveLocking>
        {{ $t("brands.create.upload-modal.tab-files") }}
      </Tab>

      <Tab value="urls" disableSaveLocking>
        {{ $t("brands.create.upload-modal.tab-urls") }}
      </Tab>
    </template>

    <TabsPanels>
      <TabPanel value="file">
        <FieldFiles
          name="files"
          :dropAreaLabel="
            $t('brands.create.upload-modal.files.drop-area-label')
          "
          size="sm"
          :maxSize="BRAND_DATA_SOURCE_MAX_FILE_SIZE_BYTES"
          :acceptedFormats="BRAND_DATA_SOURCE_ACCEPTED_FORMATS"
          :disabled="disabled"
          :deleteBackendFileConfirmFn="deleteBackendFileConfirmFn"
        >
          <template #deleteConfirmTitle>
            {{
              $t("brands.create.upload-modal.files.delete-data-source-title")
            }}
          </template>

          <template #deleteConfirmDescription="{ file }">
            {{
              $t(
                "brands.create.upload-modal.files.delete-data-source-description",
                { nameFileOrUrl: file.name },
              )
            }}
          </template>

          <template #deleteConfirmWarning>
            {{
              $t("brands.create.upload-modal.files.delete-data-source-warning")
            }}
          </template>
        </FieldFiles>
      </TabPanel>

      <TabPanel value="urls">
        <BrandUrlsField
          :disabled="disabled"
          :deleteBackendUrlConfirmFn="deleteBackendUrlConfirmFn"
        />
      </TabPanel>
    </TabsPanels>
  </Tabs>
</template>
