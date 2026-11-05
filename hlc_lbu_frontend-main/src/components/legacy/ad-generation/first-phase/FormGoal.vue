<script lang="ts" setup>
import FirstPhaseServices from "@/services/legacy/FirstPhaseServices";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const store = useAdGenerationStore();

const isLoading = ref(false);

const { handleSubmit, meta } = useFormWithErrorScrolling({
  initialValues: {
    goal: store.data.goal_description,
  },
  validationSchema: toTypedSchema(
    object().shape({
      goal: string().required(),
    }),
  ),
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data locally
  store.data.goal_description = values.goal;

  // Send data
  const response = await FirstPhaseServices.defineGoalDescription(
    store.projectId,
    values.goal,
  );

  // Save data from response
  store.data.goal_attributes_generated =
    response.data.goal_attributes_generated;
  store.data.goal_attributes_saved = undefined;

  // Go next
  store.goNext();
});
</script>

<template>
  <form @submit="onSubmit">
    <WizardCardTitle>
      {{ $t("process.goal.title") }}
      <template #button>
        <HelpButton> Help info </HelpButton>
      </template>
    </WizardCardTitle>

    <WizardCardParagraph class="tw:mb-[60px]">
      {{ $t("process.goal.description") }}
    </WizardCardParagraph>

    <div>
      <FieldsContainer class="tw:mb-11">
        <FieldTextarea
          name="goal"
          :placeholder="$t('process.goal.goal.placeholder')"
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
