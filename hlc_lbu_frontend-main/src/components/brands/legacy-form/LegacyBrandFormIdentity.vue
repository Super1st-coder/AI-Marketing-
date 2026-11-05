<script setup lang="ts">
import BrandsApi, { BrandCreateResponse } from "@/services/BrandsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { mixed, object, string } from "yup";
import { BrandFormData } from "./LegacyBrandForm.vue";
import { appLocalesArray } from "@/plugins/i18n";

const { locale, t } = useI18n();
const route = useRoute();
const router = useRouter();

const { goNext, data, saveData, setDirtyStage } = useMultiStepFormContext<
  BrandFormData | undefined
>();

const isDuplicateBrandError = (err: any): boolean => {
  const code =
    err?.code || err?.message?.code || err?.response?._data?.message?.code;
  const text =
    (typeof err?.message === "string" ? err?.message : undefined) ||
    err?.message?.text ||
    err?.response?._data?.message?.text;

  return (
    err?.message === "BRAND_ALREADY_EXISTS" ||
    code === "BRAND00" ||
    text === "ERROR - Brand name already exists"
  );
};

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      language: string().required(t("forms.required-field")),
      name: string().required(t("forms.required-field")).trim(),
      website: string().url().required(t("forms.required-field")).trim(),
      image: mixed<File>().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta, setFieldError } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      language:
        data.value?.language ??
        appLocalesArray.find((appLocale) => locale.value === appLocale.code)
          ?.apiName,
      name: data.value?.name,
      website: data.value?.website,
      image: data.value?.image,
    },
  });

const disableSaveAlert = ref(false);

const onSubmit = handleSubmit(async (values) => {
  try {
    let response: BrandCreateResponse;
    if (data.value?.id) {
      // Update existing brand
      response = await BrandsApi.updateByStep(data.value.id, {
        ...values,
        step: 0,
      });
    } else {
      // Create brand and save data
      response = await BrandsApi.create(values);
    }

    // Upload image
    await BrandsApi.uploadImage(response.data.id, values.image);

    // Set stage as dirty
    if (meta.value.dirty) {
      setDirtyStage("summary", true);
    }

    if (data.value?.id) {
      // Go to the next step
      saveData({ ...response.data, image: values.image });
      goNext({ isDirty: meta.value.dirty });
    } else {
      // Go to the settings page
      disableSaveAlert.value = true;
      await router.replace({
        name: "BrandSettings",
        params: { brandId: response.data.id },
        query: route.query,
        hash: route.hash,
      });
    }
  } catch (error: any) {
    // Intercepta duplicate brand error
    if (isDuplicateBrandError(error)) {
      setFieldError("name", t("errors.BRAND_ALREADY_EXISTS.title"));
      return;
    }
    throw error;
  }
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    >
      {{ t("brands.identity.title") }}
    </PageTitle>

    <div class="tw:flex tw:flex-col tw:gap-6 tw:lg:flex-row">
      <FieldsContainer class="tw:grow">
        <FieldLanguage
          name="language"
          :label="t('brands.identity.language.label')"
          :placeholder="t('brands.identity.language.placeholder')"
          required
          :disabled="isSubmitting"
        />

        <FieldTextarea
          name="name"
          :label="t('brands.identity.name.label')"
          :placeholder="t('brands.identity.name.placeholder')"
          required
          :rows="1"
          :disabled="isSubmitting"
        />

        <FieldTextarea
          name="website"
          :label="t('brands.identity.website.label')"
          :placeholder="t('brands.identity.website.placeholder')"
          required
          :rows="1"
          :disabled="isSubmitting"
        />
      </FieldsContainer>

      <FieldImage
        name="image"
        :label="t('brands.identity.image.label')"
        required
        class="tw:w-full tw:lg:max-w-[350px]"
        cropper
        :cropperAspectRatio="1 / 1"
        :disabled="isSubmitting"
      />
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack :to="{ name: 'BrandList' }" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />
  </FormStepLayout>
</template>
