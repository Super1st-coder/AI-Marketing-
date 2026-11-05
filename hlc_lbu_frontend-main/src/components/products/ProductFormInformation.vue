<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, object, string } from "yup";
import { ProductFormData } from "./ProductForm.vue";
import ProductsApi, { ProductCreateResponse } from "@/services/ProductsApi";
import { appLocalesArray } from "@/plugins/i18n";
import { useI18n } from "vue-i18n";

const { locale, t } = useI18n();
const route = useRoute();
const router = useRouter();

const brandId = useBrandId();

const { goNext, data, saveData, setDirtyStage } = useMultiStepFormContext<
  ProductFormData | undefined
>();

const schema = computed(() =>
  toTypedSchema(
    object({
      product: object({
        language: string().required(t("forms.required-field")),
        name: string().required(t("forms.required-field")).trim(),
        product_url: string()
          .trim()
          .test("url", t("forms.url-invalid"), (value) => {
            if (!value) return true;
            const urlToTest = /^https?:\/\//i.test(value)
              ? value
              : `https://${value}`;
            try {
              new URL(urlToTest);
              return true;
            } catch (e: unknown) {
              console.error(e);
              return false;
            }
          }),
        description: string()
          .max(500, ({ max }) => t("forms.max-characters", { max }))
          .trim(),
        files: array().of(mixed<File>().required()),
      }).test(
        "recommendedFields",
        t("products.information.please-provide-at-least-one-input"),
        (values) => {
          return (
            !!values.product_url ||
            !!values.description ||
            (values.files && values.files.length > 0)
          );
        },
      ),
    }),
  ),
);

const {
  handleSubmit,
  errors,
  submitCount,
  isSubmitting,
  meta,
  isFieldDirty,
  setFieldValue,
  values,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    product: {
      language:
        data.value?.language ??
        appLocalesArray.find((appLocale) => locale.value === appLocale.code)
          ?.apiName,
      name: data.value?.name,
      product_url: data.value?.product_url ?? undefined,
      description: data.value?.description ?? undefined,
      files: data.value?.files,
    },
  },
});

const normalizeUrl = (url: string | undefined): string | undefined => {
  if (!url || url.trim() === "") return url;
  const trimmed = url.trim();
  if (!/^https?:\/\//i.test(trimmed)) {
    return `https://${trimmed}`;
  }
  return trimmed;
};

const handleProductUrlBlur = () => {
  const currentValue = values.product?.product_url;
  const normalized = normalizeUrl(currentValue);
  if (normalized !== currentValue) {
    setFieldValue("product.product_url", normalized);
  }
};

const disableSaveAlert = ref(false);
const { confirm } = useConfirmModal();
const { confirm: confirmSuggestion } = useConfirmModal("productSuggestions");
const generalErrorMessage = ref<string>();

const onSubmit = handleSubmit(async (values) => {
  // Skip if it's locked
  generalErrorMessage.value = undefined;
  if (data.value?.locked) {
    goNext({ isDirty: false });
    return;
  }

  // Display suggestion
  if (
    !values.product.product_url ||
    !values.product.description ||
    !values.product.files ||
    values.product.files.length === 0
  ) {
    await confirmSuggestion();
  }

  let triggerGeneration = true;

  // Display and wait for the confirm modal if needed
  if (
    data.value?.mandatory_attributes_generated ||
    data.value?.optional_attributes_generated
  ) {
    if (meta.value.dirty) {
      // Display the modal if the data is dirty
      const result = await confirm();
      if (result === "close") {
        return;
      }

      triggerGeneration = result === "continue";
    } else {
      // If the data is not dirty, do not trigger prompts
      triggerGeneration = false;
    }
  }

  const exists = data.value?.id !== undefined;

  let response: ProductCreateResponse;
  if (data.value?.id) {
    // Update existing brand
    response = await ProductsApi.update(brandId, data.value.id, {
      ...values.product,
    });
  } else {
    // Create brand and save data
    response = await ProductsApi.create(brandId, values.product);
  }

  const productId = response.data.id;

  // Upload files only if they have changed and there are files
  if (
    isFieldDirty("product.files") &&
    values.product.files &&
    values.product.files.length > 0
  ) {
    const resp = await ProductsApi.uploadFiles(
      brandId,
      productId,
      values.product.files,
    );
    if (resp && String(resp.message?.code) === "UPLDOC00") {
      generalErrorMessage.value = t(
        "buyer-person.information.files.errormessage",
      );
      saveData({
        ...response.data,
        files: values.product.files,
      });
      return;
    }
  }

  // Generate attributes
  response = await ProductsApi.generateAttributes(brandId, productId, {
    trigger_prompts: triggerGeneration,
  });

  saveData({
    ...response.data,
  });

  // Set stage as dirty
  if (meta.value.dirty) {
    setDirtyStage("summary", true);
  }

  if (exists) {
    // Go to the next step
    goNext({ isDirty: meta.value.dirty });
  } else {
    // Go to the settings page
    disableSaveAlert.value = true;
    await router.replace({
      name: "ProductSettings",
      params: { productId },
      query: route.query,
      hash: route.hash,
    });
  }
});
</script>

<template>
  <FormStepLayout :maxWidth="910" @submit.prevent="onSubmit">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=faSh6NQ5wZY"
    >
      {{ t("products.information.title") }}

      <template #description>
        {{ t("products.information.description") }}
      </template>
    </PageTitle>

    <div class="tw:grid tw:grid-cols-1 tw:gap-8">
      <FieldLanguage
        name="product.language"
        :label="t('products.information.language.label')"
        :placeholder="t('products.information.language.placeholder')"
        required
        :disabled="data?.locked || isSubmitting"
      />

      <FieldTextarea
        name="product.name"
        :label="t('products.information.name.label')"
        :placeholder="t('products.information.name.placeholder')"
        required
        :rows="1"
        :disabled="data?.locked || isSubmitting"
      />

      <FieldTextarea
        name="product.product_url"
        :label="t('products.information.product-url.label')"
        :placeholder="t('products.information.product-url.placeholder')"
        leftIcon="tabler-link"
        :rows="1"
        :disabled="data?.locked || isSubmitting"
        @blur="handleProductUrlBlur"
      />

      <FieldTextarea
        name="product.description"
        :label="t('products.information.product-description.label')"
        :placeholder="t('products.information.product-description.placeholder')"
        :maxCharacters="500"
        speechRecognition
        :disabled="data?.locked || isSubmitting"
      />

      <FieldFiles
        name="product.files"
        :label="t('products.information.files.label')"
        :dropAreaLabel="t('products.information.files.input-title')"
        :disabled="data?.locked || isSubmitting"
      />
    </div>

    <Alert v-if="errors.product && submitCount > 0" type="error" autoScroll>
      {{ errors.product }}
    </Alert>

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack :to="{ name: 'ProductList', params: { brandId } }" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalConfirmRegeneration />

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />

    <ModalConfirmSuggestions name="productSuggestions">
      <template #title>{{ t("products.information.modal-title") }}</template>

      <template #description>
        {{ t("products.information.modal-description") }}
      </template>
    </ModalConfirmSuggestions>
  </FormStepLayout>
</template>
