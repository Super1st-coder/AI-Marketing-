<script setup lang="ts">
import BrandsApi from "@/services/BrandsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { BrandFormData } from "./LegacyBrandForm.vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const { goNext, goBack, data, saveData, setDirtyStage, getIsStageDirty } =
  useMultiStepFormContext<BrandFormData>();

const schema = computed(() =>
  toTypedSchema(
    object({
      industry: string().required(t("forms.required-field")).trim(),
      markets: string().required(t("forms.required-field")).trim(),
      geography: string().required(t("forms.required-field")).trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    industry: data.value?.industry ?? undefined,
    markets: data.value?.markets ?? undefined,
    geography: data.value?.geography ?? undefined,
  },
});

const { confirm } = useConfirmModal();

const onSubmit = handleSubmit(async (values) => {
  let triggerGeneration = true;

  // Display and wait for the confirm modal if needed
  if (data.value.attributes_generated) {
    if (meta.value.dirty || getIsStageDirty("summary")) {
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

  // Update existing brand
  const response = await BrandsApi.updateByStep(data.value.id, {
    ...values,
    step: 3,
    trigger_prompts: triggerGeneration,
  });

  // Save the data
  saveData({ ...response.data });
  setDirtyStage("summary", false);
  goNext({ isDirty: meta.value.dirty });
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <PageTitle helpButton>{{ t("brands.markets.title") }}</PageTitle>

    <FieldsContainer>
      <FieldTextarea
        name="industry"
        :label="t('brands.markets.industry.label')"
        :placeholder="t('brands.markets.industry.placeholder')"
        required
        :rows="1"
        :disabled="isSubmitting"
      />

      <FieldTextarea
        name="markets"
        :label="t('brands.markets.markets.label')"
        :placeholder="t('brands.markets.markets.placeholder')"
        required
        :rows="1"
        :disabled="isSubmitting"
      />

      <FieldTextarea
        name="geography"
        :label="t('brands.markets.geography.label')"
        :placeholder="t('brands.markets.geography.placeholder')"
        required
        :rows="1"
        :disabled="isSubmitting"
      />
    </FieldsContainer>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
    <ModalConfirmRegeneration />
  </FormStepLayout>
</template>
