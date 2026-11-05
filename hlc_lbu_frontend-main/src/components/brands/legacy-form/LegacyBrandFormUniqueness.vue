<script setup lang="ts">
import BrandsApi from "@/services/BrandsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { BrandFormData } from "./LegacyBrandForm.vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const { goBack, goNext, data, saveData, setDirtyStage } =
  useMultiStepFormContext<BrandFormData>();

const schema = computed(() =>
  toTypedSchema(
    object({
      uniqueness: string().required(t("forms.required-field")).trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    uniqueness: data.value.uniqueness ?? undefined,
  },
});

const onSubmit = handleSubmit(async (values) => {
  // Update existing brand
  const response = await BrandsApi.updateByStep(data.value.id, {
    ...values,
    step: 2,
  });

  // Save the data
  saveData({ ...response.data });
  if (meta.value.dirty) {
    setDirtyStage("summary", true);
  }
  goNext({ isDirty: meta.value.dirty });
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <PageTitle helpButton>{{ t("brands.uniqueness.title") }}</PageTitle>

    <FieldsContainer>
      <FieldTextarea
        name="uniqueness"
        :label="t('brands.uniqueness.label')"
        :placeholder="t('brands.uniqueness.placeholder')"
        required
        speechRecognition
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
  </FormStepLayout>
</template>
