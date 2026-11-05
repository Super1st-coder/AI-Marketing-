<script lang="ts" setup>
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import FirstPhaseServices from "@/services/legacy/FirstPhaseServices";

const store = useAdGenerationStore();

const isLoading = ref(false);

const { handleSubmit, meta } = useFormWithErrorScrolling({
  initialValues: {
    targetCustomer: store.data.target_customer_description,
  },
  validationSchema: toTypedSchema(
    object().shape({
      targetCustomer: string().required(),
    }),
  ),
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data locally
  store.data.target_customer_description = values.targetCustomer;

  // Send data
  const response = await FirstPhaseServices.defineTargetConsumerDescription(
    store.projectId,
    values.targetCustomer,
  );

  // Save data from response
  store.data.target_customer_attributes_generated =
    response.data.target_customer_attributes_generated;
  store.data.target_customer_attributes_saved = undefined;

  // Go next
  store.goNext();
});
</script>

<template>
  <form @submit="onSubmit">
    <WizardCardTitle>
      {{ $t("process.your-target.title") }}
      <template #button>
        <HelpButton> Help info </HelpButton>
      </template>
    </WizardCardTitle>

    <WizardCardParagraph class="tw:mb-[60px]">
      {{ $t("process.your-target.description") }}
    </WizardCardParagraph>

    <div>
      <FieldsContainer class="tw:mb-11">
        <FieldTextarea
          name="targetCustomer"
          :placeholder="$t('process.your-target.target-customer.placeholder')"
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
