<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object } from "yup";
import { CampaignFormData } from "./CampaignForm.vue";
import ProjectsApi from "@/services/projects/ProjectsApi";
import { LlmOutputError, UnidentifiedError } from "@/services/common-errors";
import { categorySelectorSchema } from "../forms/category-selector/categorySelectorSchema";
import {
  transformCategorySelectorToJson,
  getCategorySelector,
} from "../forms/category-selector/categorySelectorUtils";
import CampaignsApi from "@/services/projects/CampaignsApi";
import BuyerPersonasApi from "@/services/BuyerPersonasApi";

const { t } = useI18n();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<CampaignFormData>();

const brandId = useBrandId();
const projectId = useProjectId();

// Fetch project
const { data: project } = await ProjectsApi.getOne(brandId, projectId);
if (!project.bperson) {
  throw new UnidentifiedError();
}

// Fetch buyer person
const { data: buyerPerson } = await BuyerPersonasApi.getOne(
  brandId,
  project.bperson.id,
);
if (!buyerPerson.mandatory_attributes_saved) {
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
        buyerPerson.mandatory_attributes_saved,
        data.value.bperson_details,
      ),
    ],
  },
  keepValuesOnUnmount: true,
});

const generalErrorMessage = ref<string>();

const onSubmit = handleSubmit(async (values) => {
  try {
    generalErrorMessage.value = undefined;

    let response = await CampaignsApi.setBuyerPersonDetails(
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
  } catch (error) {
    if (error instanceof LlmOutputError) {
      generalErrorMessage.value = t(`errors.${error.message}.title`);
    } else {
      throw error;
    }
  }
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
      {{ $t("campaigns.conceptbuyer.title") }}
      <template #description>
        {{ $t("campaigns.conceptbuyer.description") }}
      </template>
    </PageTitle>

    <CategorySelector
      name="categories"
      :label="$t('campaigns.conceptbuyer.labeltext')"
    />

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
