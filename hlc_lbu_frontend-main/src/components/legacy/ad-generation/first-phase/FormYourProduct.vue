<script lang="ts" setup>
import FirstPhaseServices from "@/services/legacy/FirstPhaseServices";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const store = useAdGenerationStore();

const isLoading = ref(false);

const { handleSubmit, meta } = useFormWithErrorScrolling({
  initialValues: {
    brandName: store.data.brand_name,
    productName: store.data.product_name,
    producDetailsUrl: store.data.product_url,
    productFaq: store.data.faq_product_url,
  },
  validationSchema: toTypedSchema(
    object().shape({
      brandName: string().required(),
      productName: string().required(),
      producDetailsUrl: string().required(),
      productFaq: string().required(),
    }),
  ),
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data locally
  store.data.brand_name = values.brandName;
  store.data.product_name = values.productName;
  store.data.product_url = values.producDetailsUrl;
  store.data.faq_product_url = values.productFaq;

  // Send data
  const response = await FirstPhaseServices.defineProductDescription(
    store.projectId,
    values.brandName,
    values.productName,
    values.producDetailsUrl,
    values.productFaq,
  );

  // Save data from response
  store.data.product_attributes_generated =
    response.data.product_attributes_generated;
  store.data.product_attributes_saved = undefined;

  // Go next
  store.goNext();
});
</script>

<template>
  <form @submit.prevent="onSubmit">
    <WizardCardTitle>
      {{ $t("process.your-product.title") }}
      <template #button>
        <HelpButton> Help info </HelpButton>
      </template>
    </WizardCardTitle>

    <WizardCardParagraph class="tw:mb-[60px]">
      {{ $t("process.your-product.description") }}
    </WizardCardParagraph>

    <div>
      <FieldsContainer class="tw:mb-11">
        <FieldText
          name="brandName"
          :label="$t('process.your-product.brand-name.label')"
          :placeholder="$t('process.your-product.brand-name.placeholder')"
          required
        />

        <FieldText
          name="productName"
          :label="$t('process.your-product.product-name.label')"
          :placeholder="$t('process.your-product.product-name.placeholder')"
          required
        />

        <FieldText
          name="producDetailsUrl"
          :label="$t('process.your-product.product-details.label')"
          :placeholder="$t('process.your-product.product-details.placeholder')"
          required
        />

        <FieldTextarea
          name="productFaq"
          :label="$t('process.your-product.product-faq.label')"
          :placeholder="$t('process.your-product.product-faq.placeholder')"
          required
        />
      </FieldsContainer>

      <WizardCardActions>
        <WizardButtonGoBack @click="store.goBack" />

        <WizardButtonNext :disabled="!meta.valid" :isLoading="isLoading" />
      </WizardCardActions>
    </div>
  </form>
</template>
