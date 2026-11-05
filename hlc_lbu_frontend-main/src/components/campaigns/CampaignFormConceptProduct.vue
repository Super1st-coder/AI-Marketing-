<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object } from "yup";
import { CampaignFormData } from "./CampaignForm.vue";
import ProjectsApi from "@/services/projects/ProjectsApi";
import ProductsApi from "@/services/ProductsApi";
import { UnidentifiedError } from "@/services/common-errors";
import { categorySelectorSchema } from "../forms/category-selector/categorySelectorSchema";
import {
  transformCategorySelectorToJson,
  getCategorySelector,
} from "../forms/category-selector/categorySelectorUtils";
import CampaignsApi from "@/services/projects/CampaignsApi";

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<CampaignFormData>();

const brandId = useBrandId();
const projectId = useProjectId();

// Fetch project
const { data: project } = await ProjectsApi.getOne(brandId, projectId);
if (!project.product) {
  throw new UnidentifiedError();
}

// Fetch product
const { data: product } = await ProductsApi.getOne(brandId, project.product.id);
if (!product.optional_attributes_saved || !product.mandatory_attributes_saved) {
  throw new UnidentifiedError();
}

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: toTypedSchema(
    object().shape({
      categories: categorySelectorSchema,
    }),
  ),
  initialValues: {
    categories: [
      ...getCategorySelector(
        product.mandatory_attributes_saved,
        data.value.product_details,
      ),
      ...getCategorySelector(
        product.optional_attributes_saved,
        data.value.product_details,
      ),
    ],
  },
  keepValuesOnUnmount: true,
});

const onSubmit = handleSubmit(async (values) => {
  let response = await CampaignsApi.setProductDetails(
    brandId,
    projectId,
    data.value.id,
    transformCategorySelectorToJson(values.categories),
  );

  // Save data and go next
  saveData({
    ...response.data,
  });
  goNext();
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="concept" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=4VX0rxSTcog"
    >
      {{ $t("campaigns.conceptproduct.title") }}
      <template #description>
        {{ $t("campaigns.conceptproduct.description") }}
      </template>
    </PageTitle>

    <CategorySelector
      name="categories"
      :label="$t('campaigns.conceptproduct.labeltext')"
    />

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
