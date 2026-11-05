<script lang="ts" setup>
import FirstPhaseServices from "@/services/legacy/FirstPhaseServices";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const store = useAdGenerationStore();

const isLoading = ref(false);

const { handleSubmit, meta } = useFormWithErrorScrolling({
  initialValues: {
    element: store.data.hypothesis_element_description,
  },
  validationSchema: toTypedSchema(
    object().shape({
      element: string().required(),
    }),
  ),
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data locally
  store.data.hypothesis_element_description = values.element;

  // Send data
  const response = await FirstPhaseServices.defineHypothesisDescription(
    store.projectId,
    values.element,
  );

  // Save data from response
  store.data.hypothesis_element_attributes_generated =
    response.data.hypothesis_element_attributes_generated;
  store.data.hypothesis_element_attributes_saved = undefined;

  // Go next
  store.goNext();
});
</script>

<template>
  <form @submit="onSubmit">
    <WizardCardTitle>
      {{ $t("process.element.title") }}
      <template #button>
        <HelpButton> Help info </HelpButton>
      </template>
    </WizardCardTitle>

    <WizardCardParagraph class="tw:mb-[60px]">
      {{ $t("process.element.description") }}
    </WizardCardParagraph>

    <div>
      <FieldsContainer class="tw:mb-11">
        <FieldTextarea
          name="element"
          :placeholder="$t('process.element.element.placeholder')"
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
