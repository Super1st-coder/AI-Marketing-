<script setup lang="ts">
import NewBrandsApi, {
  BrandAlreadyExistsError,
  BrandLimitReachedError,
} from "@/services/NewBrandsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, object, string } from "yup";

const { t } = useI18n();
const router = useRouter();

const isOpen = defineModel<boolean>({ required: true });
const generalErrorMessage = ref<string | undefined>(undefined);

const props = defineProps<{
  brandName: string;
  brandWebsiteUrl: string;
  brandLanguage: string;
}>();

const emit = defineEmits<{
  brandAlreadyExists: [];
  brandLimitReached: [];
}>();

const currentTab = ref<"file" | "urls">("file");
const isLoading = ref(false);
const isReady = ref(false);

watch(isOpen, (isOpen) => {
  if (!isOpen) {
    isLoading.value = false;
    isReady.value = false;
  }
});

const schema = computed(() =>
  toTypedSchema(
    object({
      files: array()
        .of(mixed<File>().required())
        .min(1, t("forms.required-field"))
        .required(t("forms.required-field")),
      urls: array().of(string().url().trim()),
    }),
  ),
);

const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
  keepValuesOnUnmount: true,
  initialValues: {
    urls: [""],
  },
});

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  generalErrorMessage.value = undefined;
  isLoading.value = true;

  try {
    // Create brand with AI
    const { data: brand } = await NewBrandsApi.createByAI({
      name: props.brandName,
      website_url: props.brandWebsiteUrl,
      language: props.brandLanguage,
      urls:
        values.urls?.filter(
          (url): url is string => url !== undefined && url !== "",
        ) ?? [],
      files: values.files,
    });

    // Loader
    isReady.value = true;
    await sleep(BRAND_RING_LOADER_COMPLETION_HOLD_MS);

    // Close modal and navigate to the settings page
    isOpen.value = false;
    router.push({
      name: "BrandSettings",
      params: { brandId: brand.id },
      query: { justCreated: "extracted" },
    });
  } catch (error: unknown) {
    if (error instanceof BrandAlreadyExistsError) {
      isOpen.value = false;
      emit("brandAlreadyExists");
      return;
    }

    if (error instanceof BrandLimitReachedError) {
      isOpen.value = false;
      isLoading.value = false;
      emit("brandLimitReached");
      return;
    }

    generalErrorMessage.value = t("brands.create.errors.create-brand");
    isLoading.value = false;
  }
});
</script>

<template>
  <Modal
    v-model="isOpen"
    alignment="top"
    :maxWidth="600"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    v-slot="{ close }"
  >
    <div v-if="isLoading" class="tw:px-6 tw:py-8">
      <ProgressRingLoader
        :steps="[
          t(
            'brands.create.upload-modal.loading-steps.reading-brand-guidelines',
          ),
          t(
            'brands.create.upload-modal.loading-steps.extracting-color-palette',
          ),
          t('brands.create.upload-modal.loading-steps.identifying-assets'),
          t('brands.create.upload-modal.loading-steps.finalizing-profile'),
        ]"
        :interval="BRAND_CREATION_RING_LOADER_INTERVAL_MS"
        :completed="isReady"
      >
        <template #title>
          {{ $t("brands.create.upload-modal.loading-title") }}
        </template>

        <template #description>
          {{ $t("brands.create.upload-modal.loading-description") }}
        </template>
      </ProgressRingLoader>
    </div>
    <form v-else @submit.prevent="onSubmit">
      <ModalHeader>
        {{ $t("brands.create.upload-modal.title") }}

        <template #description>
          {{ $t("brands.create.upload-modal.description") }}
        </template>
      </ModalHeader>

      <ModalBody class="tw:grid tw:grid-cols-1 tw:gap-6">
        <BrandFilesAndUrlsTabs v-model="currentTab" :disabled="isSubmitting" />

        <Alert v-if="generalErrorMessage" type="error">
          {{ generalErrorMessage }}
        </Alert>
      </ModalBody>

      <ModalFooter>
        <Button
          color="secondary"
          variant="outlined"
          @click="close"
          type="button"
          :disabled="isSubmitting"
        >
          {{ $t("global.cancel") }}
        </Button>

        <Button :isLoading="isSubmitting">
          {{ $t("brands.create.upload-modal.submit") }}
        </Button>
      </ModalFooter>
    </form>
  </Modal>
</template>
