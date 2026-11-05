<script setup lang="ts">
import type { BrandSavedDataSource } from "@/components/brands/common/BrandFilesAndUrlsTabs.vue";
import NewBrandsApi from "@/services/NewBrandsApi";
import type {
  EditBrandDataSourceDeletion,
  UploadDataSourceBody,
} from "@/services/NewBrandsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, object, string } from "yup";

const props = defineProps<{
  loaderSteps: string[];
  section: UploadDataSourceBody["section"];
  loaderInterval?: number;
  beforeSubmitFn?: () => Promise<void>;
  afterSubmitFn?: () => Promise<void>;
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const store = useBrandFormStore();

const screen = ref<"settings" | "loader" | "success">("settings");
const isReady = ref(false);
const pendingDeleteDataSources = ref<EditBrandDataSourceDeletion[]>([]);
const generalErrorMessage = ref<string | undefined>(undefined);

const schema = computed(() =>
  toTypedSchema(
    object({
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
      files: getInitialFiles(),
      urls: getInitialUrls(),
    },
  });

const onSubmit = handleSubmit(async (values) => {
  generalErrorMessage.value = undefined;

  // Wait for response
  try {
    await props.beforeSubmitFn?.();

    // Delete sources
    for (const {
      data_source_id,
      data_source_name,
    } of pendingDeleteDataSources.value) {
      await NewBrandsApi.deleteDataSource({
        brand_id: store.brandId,
        data_source_id,
        data_source_name,
      });
    }

    // Get the newly uploaded files
    const newFiles = values.files.filter(
      (file): file is File => file instanceof File,
    );

    // Get the newly added URLs
    const newUrls = values.urls
      .filter((url): url is string => typeof url === "string")
      .map((url) => url.trim())
      .filter((url) => url !== "");

    if (newFiles.length > 0 || newUrls.length > 0) {
      // Loader screen
      screen.value = "loader";

      await NewBrandsApi.uploadDataSource({
        brand_id: store.brandId,
        files: newFiles,
        urls: newUrls,
        section: props.section,
      });

      // Display the last step in loader for a moment
      isReady.value = true;
      await sleep(BRAND_RING_LOADER_COMPLETION_HOLD_MS);
    }

    // Display the success screen
    await props.afterSubmitFn?.();
    screen.value = "success";
  } catch (error) {
    console.log(error);

    generalErrorMessage.value = t(
      "brands.settings.edit-modal.error-update-brand",
    );

    // Go back to the initial screen
    screen.value = "settings";
  } finally {
    pendingDeleteDataSources.value = [];

    // Refetch the brand
    await store.refetch({ refetchDataSources: true });

    // Reset files in form
    resetForm({ values: { files: getInitialFiles(), urls: getInitialUrls() } });
  }
});

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
    :maxWidth="600"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      <slot name="title" />

      <template #description>
        <slot name="description" />
      </template>

      <template v-if="$slots.warning" #after>
        <Alert type="warning" class="tw:mt-6">
          <slot name="warning" />
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody class="tw:grid tw:grid-cols-1 tw:gap-10">
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
  <!-- Ring loader modal -->
  <BrandRingLoaderModal
    v-else-if="screen === 'loader'"
    v-model="isOpen"
    :isReady="isReady"
    :interval="loaderInterval"
    :steps="loaderSteps"
  />
  <!-- Final success modal -->
  <BrandReadyForReviewModal v-else-if="screen === 'success'" v-model="isOpen" />
</template>
