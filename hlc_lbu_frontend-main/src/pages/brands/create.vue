<script lang="ts" setup>
import NewBrandsApi, {
  BrandAlreadyExistsError,
  BrandLimitReachedError,
} from "@/services/NewBrandsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const router = useRouter();
const { t } = useI18n();
const appLocaleData = useAppLocaleData();
usePageTitle(() => t("routes.create-brand"));

const submissionType = ref<"manual" | "file">("manual");
const isUploadFileModalOpen = ref(false);
/** Shown when the company has used all its brand licenses (Gate 3). */
const brandLimitMessage = ref<string>();

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string().required(t("forms.required-field")).trim(),
      language: string().required(t("forms.required-field")),
      website_url: string().url().required(t("forms.required-field")).trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, setFieldError, values } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      language: appLocaleData.value.apiName,
    },
  });

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  // Open the upload file modal
  if (submissionType.value === "file") {
    isUploadFileModalOpen.value = true;
    return;
  }

  brandLimitMessage.value = undefined;

  try {
    // Create brand
    const { data: brand } = await NewBrandsApi.create({
      name: values.name,
      website_url: values.website_url,
      language: values.language,
    });

    // Navigate to the settings page
    router.push({
      name: "BrandSettings",
      params: { brandId: brand.id },
      query: { justCreated: "manual" },
    });
  } catch (error: unknown) {
    if (error instanceof BrandAlreadyExistsError) {
      setFieldError("name", t("brands.create.errors.brand-already-exists"));
      return;
    }
    if (error instanceof BrandLimitReachedError) {
      handleBrandLimitReached();
      return;
    }
    throw error;
  }
});

const handleUpload = () => {
  submissionType.value = "file";
  onSubmit();
};

const handleManual = () => {
  submissionType.value = "manual";
  onSubmit();
};

const handleBrandAlreadyExists = () => {
  setFieldError("name", t("brands.create.errors.brand-already-exists"));
};

const handleBrandLimitReached = () => {
  brandLimitMessage.value = t("brands.create.errors.brand-limit");
};
</script>

<template>
  <GenericSubLayout belowNavbar>
    <template #headerBackAction>
      <RouterLink :to="{ name: 'BrandList' }">
        <Icon icon="tabler-arrow-left" class="tw:text-2xl" />
      </RouterLink>
    </template>

    <template #headerLeft>
      <h2 class="tw:line-clamp-1 tw:font-medium">
        {{ $t("brands.create.header-title") }}
      </h2>
    </template>

    <Container :maxWidth="646" class="tw:py-10">
      <form @submit.prevent="onSubmit" class="tw:flex tw:flex-col tw:gap-10">
        <PageTitle>
          {{ $t("brands.create.page-title") }}

          <template #description>
            {{ $t("brands.create.page-description") }}
          </template>
        </PageTitle>

        <Alert v-if="brandLimitMessage" type="warning" autoScroll>
          {{ brandLimitMessage }}
        </Alert>

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

        <div class="tw:flex tw:flex-col">
          <h2 class="tw:mb-4 tw:font-semibold">
            {{ $t("brands.create.choose-way-heading") }}
          </h2>

          <CardBase
            is="button"
            class="tw:mb-7 tw:flex tw:gap-3 tw:p-4"
            type="button"
            hoverColor="primary"
            @click="handleUpload"
            :disabled="isSubmitting"
          >
            <Icon icon="tabler:cloud-upload" class="tw:text-2xl" />

            <div>
              <h3 class="tw:font-bold">
                {{ $t("brands.create.upload-file-title") }}
              </h3>

              <p class="tw:text-sm tw:text-gray-500">
                {{ $t("brands.create.upload-file-description") }}
              </p>
            </div>
          </CardBase>

          <CardBase
            is="button"
            class="tw:flex tw:gap-3 tw:p-4"
            type="button"
            hoverColor="primary"
            @click="handleManual"
            :disabled="isSubmitting"
          >
            <Icon icon="tabler-plus" class="tw:text-2xl" />

            <div>
              <h3 class="tw:font-bold">
                {{ $t("brands.create.create-manually-title") }}
              </h3>

              <p class="tw:text-sm tw:text-gray-500">
                {{ $t("brands.create.create-manually-description") }}
              </p>

              <CircleLoaderDefault
                v-if="isSubmitting && submissionType === 'manual'"
              />
            </div>
          </CardBase>
        </div>
      </form>
    </Container>
  </GenericSubLayout>

  <CreateBrandUploadFileModal
    v-model="isUploadFileModalOpen"
    :brandName="values.name ?? ''"
    :brandWebsiteUrl="values.website_url ?? ''"
    :brandLanguage="values.language ?? ''"
    @brandAlreadyExists="handleBrandAlreadyExists"
    @brandLimitReached="handleBrandLimitReached"
  />
</template>
