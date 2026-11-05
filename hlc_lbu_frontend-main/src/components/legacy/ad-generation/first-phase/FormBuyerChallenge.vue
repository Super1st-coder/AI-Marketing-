<script lang="ts" setup>
import FirstPhaseServices from "@/services/legacy/FirstPhaseServices";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const store = useAdGenerationStore();

const isLoading = ref(false);

const { handleSubmit, meta } = useFormWithErrorScrolling({
  initialValues: {
    buyerChallengeFeatures: store.data.advantages_description,
  },
  validationSchema: toTypedSchema(
    object().shape({
      buyerChallengeFeatures: string().required(),
    }),
  ),
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data locally
  store.data.advantages_description = values.buyerChallengeFeatures;

  // Send data
  const response = await FirstPhaseServices.defineAdvantagesDescription(
    store.projectId,
    values.buyerChallengeFeatures,
  );

  // Save data from response
  store.data.advantages_attributes_generated =
    response.data.advantages_attributes_generated;
  store.data.advantages_attributes_saved = undefined;

  // Go next
  store.goNext();
});
</script>

<template>
  <form @submit="onSubmit">
    <WizardCardTitle>
      {{ $t("process.buyer-challenge.title") }}
      <template #button>
        <HelpButton> Help info </HelpButton>
      </template>
    </WizardCardTitle>

    <WizardCardParagraph class="tw:mb-[60px]">
      {{ $t("process.buyer-challenge.description") }}
    </WizardCardParagraph>

    <div>
      <FieldsContainer class="tw:mb-11">
        <FieldTextarea
          name="buyerChallengeFeatures"
          :placeholder="
            $t('process.buyer-challenge.buyer-challenge-features.placeholder')
          "
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
