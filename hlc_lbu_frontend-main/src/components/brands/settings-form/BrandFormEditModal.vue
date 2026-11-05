<script setup lang="ts">
import type { BrandSavedDataSource } from "@/components/brands/common/BrandFilesAndUrlsTabs.vue";
import { UnidentifiedError } from "@/services/common-errors";
import NewBrandsApi, {
  type EditBrandDataSourceDeletion,
} from "@/services/NewBrandsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { InferOutput } from "vee-validate";
import { array, mixed, object, string } from "yup";

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const store = useBrandFormStore();

const screen = ref<"settings" | "confirm" | "loader" | "success">("settings");
const isReady = ref(false);

const generalErrorMessage = ref<string | undefined>(undefined);

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string().required(t("forms.required-field")).trim(),
      language: string().required(t("forms.required-field")),
      website_url: string().url().required(t("forms.required-field")).trim(),
      files: array()
        .of(mixed<File | BrandSavedDataSource>().required())
        .required(),
      urls: array()
        .of(
          mixed<string | BrandSavedDataSource>()
            .optional()
            .test("url-or-backend", function (value) {
              // Allow empty values
              if (value === undefined || value === "") {
                return true;
              }

              // Allow back-end value
              if (typeof value === "object") {
                return true;
              }

              // Validate URL string
              if (typeof value === "string") {
                try {
                  string().url().trim().validateSync(value);
                  return true;
                } catch (e: unknown) {
                  if (e instanceof Error) {
                    return this.createError({ message: e.message });
                  }
                }
              }

              return this.createError({ message: t("forms.required-field") });
            }),
        )
        .required(),
    }),
  ),
);

type OutputType = InferOutput<typeof schema.value>;

const pendingData = ref<OutputType | undefined>(undefined);
const pendingDeleteDataSources = ref<EditBrandDataSourceDeletion[]>([]);

function getInitialFiles() {
  return store.dataSources
    .filter((source) => source.type === "DOC")
    .map(({ id, name }) => ({ id, name }));
}

function getInitialUrls() {
  return store.dataSources
    .filter((source) => source.type === "URL")
    .map(({ id, name }) => ({ id, name }));
}

const { handleSubmit, isSubmitting, resetForm, meta } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    keepValuesOnUnmount: true,
    initialValues: {
      name: store.brand.name,
      language: store.brand.language ?? undefined,
      // website_url could come as an empty string ""
      website_url:
        store.brand.website_url && store.brand.website_url !== ""
          ? store.brand.website_url
          : undefined,
      files: getInitialFiles(),
      urls: getInitialUrls(),
    },
  });

const onSubmit = handleSubmit(async (values) => {
  generalErrorMessage.value = undefined;
  pendingData.value = values;

  try {
    // Display confirmation screen
    screen.value = "confirm";
  } catch (error) {
    console.log(error);
  }
});

async function handleCancel() {
  // Take the user back to the initial screen
  screen.value = "settings";
}

async function performUpdate(analyze: boolean): Promise<boolean> {
  try {
    if (!pendingData.value) {
      throw new UnidentifiedError();
    }

    const values = pendingData.value;

    // Get the newly uploaded files
    const newFiles = values.files.filter(
      (file): file is File => file instanceof File,
    );

    // Get the newly added URLs
    const newUrls = values.urls
      .filter((url): url is string => typeof url === "string")
      .map((url) => url.trim())
      .filter((url) => url !== "");

    // Create an array of sources to delete
    const deletePayload =
      pendingDeleteDataSources.value.length > 0
        ? [...pendingDeleteDataSources.value]
        : undefined;

    await NewBrandsApi.editBrand({
      brand_id: store.brandId,
      name: values.name,
      website_url: values.website_url,
      language: values.language,
      files: newFiles,
      urls: newUrls,
      analyze,
      delete_data_sources: deletePayload,
    });

    return true;
  } catch (error) {
    console.log(error);

    generalErrorMessage.value = t(
      "brands.settings.edit-modal.error-update-brand",
    );
    return false;
  } finally {
    pendingDeleteDataSources.value = [];

    // Refetch the brand
    await store.refetch({ refetchDataSources: true });

    // Reset files in form
    resetForm({ values: { files: getInitialFiles(), urls: getInitialUrls() } });
  }
}

async function handleConfirmWithoutAnalysis() {
  // Wait for response
  const result = await performUpdate(false);

  if (result) {
    // Success screen if the update was successful
    screen.value = "success";
  } else {
    // Go back to the initial screen if the update failed
    screen.value = "settings";
  }
}

async function handleConfirmWithAnalysis() {
  // Loader screen
  screen.value = "loader";

  // Wait for response
  const result = await performUpdate(true);

  if (result) {
    // Display the last step in loader and then the success screen if
    // the update was successful

    isReady.value = true;
    await sleep(BRAND_RING_LOADER_COMPLETION_HOLD_MS);

    // Success screen
    screen.value = "success";
  } else {
    // Go back to the initial screen if the update failed
    screen.value = "settings";
  }
}

async function handleConfirmDeleteBackendFile(
  file: BrandSavedDataSource,
): Promise<boolean> {
  pendingDeleteDataSources.value.push({
    data_source_id: file.id,
    data_source_name: file.name,
  });

  return true;
}
</script>

<template>
  <Modal
    v-if="screen === 'settings'"
    v-model="isOpen"
    alignment="top"
    :maxWidth="600"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ $t("brands.settings.edit-modal.title") }}

      <template #description>
        {{ $t("brands.settings.edit-modal.description") }}
      </template>
    </ModalHeader>

    <ModalBody class="tw:grid tw:grid-cols-1 tw:gap-10">
      <FieldText
        name="name"
        :label="$t('brands.create.name.label')"
        :placeholder="$t('brands.create.name.placeholder')"
        :disabled="isSubmitting"
        required
      />

      <FieldLanguage
        name="language"
        :label="$t('brands.create.language.label')"
        :placeholder="$t('brands.create.language.placeholder')"
        :disabled="isSubmitting"
        required
      >
        <template #hint>
          {{ $t("brands.create.language.description") }}
        </template>
      </FieldLanguage>

      <FieldText
        name="website_url"
        :description="$t('brands.create.website-url.description')"
        :label="$t('brands.create.website-url.label')"
        :placeholder="$t('brands.create.website-url.placeholder')"
        :disabled="isSubmitting"
        required
      />

      <BrandFilesAndUrlsTabs
        :disabled="isSubmitting"
        :deleteBackendFileConfirmFn="handleConfirmDeleteBackendFile"
        :deleteBackendUrlConfirmFn="handleConfirmDeleteBackendFile"
      />

      <Alert v-if="generalErrorMessage" type="error">
        {{ generalErrorMessage }}
      </Alert>
    </ModalBody>

    <ModalFooter>
      <Button
        color="secondary"
        variant="outlined"
        type="button"
        :disabled="isSubmitting"
        @click="close"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button :disabled="!meta.dirty" :isLoading="isSubmitting">
        {{ $t("global.process-and-update") }}
      </Button>
    </ModalFooter>
  </Modal>
  <!-- Confirmation modal -->
  <BrandSaveChangesModal
    v-else-if="screen === 'confirm'"
    v-model="isOpen"
    @cancel="handleCancel"
    @confirmWithoutAnalysis="handleConfirmWithoutAnalysis"
    @confirmWithAnalysis="handleConfirmWithAnalysis"
  />
  <!-- Ring loader modal -->
  <BrandRingLoaderModal
    v-else-if="screen === 'loader'"
    v-model="isOpen"
    :isReady="isReady"
    :interval="BRAND_EDITION_RING_LOADER_INTERVAL_MS"
    :steps="[
      $t('brands.settings.edit-modal.loader-steps.0'),
      $t('brands.settings.edit-modal.loader-steps.1'),
      $t('brands.settings.edit-modal.loader-steps.2'),
    ]"
  />
  <!-- Final success modal -->
  <BrandReadyForReviewModal v-else-if="screen === 'success'" v-model="isOpen" />
</template>
