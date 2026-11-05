<script lang="ts" setup>
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import FirstPhaseServices from "@/services/legacy/FirstPhaseServices";

const store = useAdGenerationStore();

const isLoading = ref(false);

const schema = toTypedSchema(
  object().shape({
    hypothesis: string().required(),
  }),
);

const { handleSubmit, meta } = useFormWithErrorScrolling({
  initialValues: {
    hypothesis: store.data.marketing_hypothesis,
  },
  validationSchema: schema,
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data locally
  store.data.marketing_hypothesis = values.hypothesis;

  // Send data
  await FirstPhaseServices.defineMarketingHypothesis(
    store.projectId,
    values.hypothesis,
  );

  store.goNext();
});
</script>

<template>
  <form
    @submit="onSubmit"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        {{ $t("process.hypothesis.title") }}
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        {{ $t("process.hypothesis.description") }}
      </WizardCardParagraph>
    </div>

    <FieldsContainer>
      <FieldTextarea
        name="hypothesis"
        :label="$t('process.hypothesis.hypothesis.label')"
        :placeholder="$t('process.hypothesis.hypothesis.placeholder')"
        required
      />
    </FieldsContainer>

    <WizardCardActions>
      <WizardButtonGoBack :to="{ name: 'AdGenerationGettingStarted' }" />

      <WizardButtonNext :disabled="!meta.valid" :isLoading="isLoading" />
    </WizardCardActions>
  </form>
</template>
