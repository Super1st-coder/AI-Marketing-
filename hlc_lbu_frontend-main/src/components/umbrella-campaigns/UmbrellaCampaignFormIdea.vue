<script setup lang="ts">
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
} from "@/services/projects/UmbrellaCampaignsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const { t } = useI18n();

const brandId = useBrandId();
const projectId = useProjectId();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<UmbrellaCampaignData>();

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      big_idea: string()
        .max(500, ({ max }) => t("forms.max-characters", { max }))
        .trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    big_idea: data.value.central_idea ?? undefined,
  },
});

const onSubmit = handleSubmit(async (values) => {
  if (values.big_idea) {
    const response = await UmbrellaCampaignsApi.setCentralIdea(
      brandId,
      projectId,
      data.value.id,
      values.big_idea,
    );

    saveData(response.data);
  }

  goNext();
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="bigIdea" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=xN-oeSkuy_A"
    >
      {{ t("umbrella-campaign.step-big-idea.title") }}

      <template #description>
        {{ t("umbrella-campaign.step-big-idea.description") }}
      </template>
    </PageTitle>

    <FieldsContainer>
      <FieldTextarea
        name="big_idea"
        :placeholder="t('umbrella-campaign.step-big-idea.placeholder')"
        speechRecognition
        :maxCharacters="500"
        required
      />
    </FieldsContainer>

    <Button
      variant="label"
      color="primary"
      size="lg"
      class="tw:mt-4 tw:flex tw:w-auto tw:items-center tw:gap-[7px] tw:self-start"
      type="button"
      @click="goNext"
    >
      <template #before>
        <span
          class="tw:inline-flex tw:h-[18px] tw:w-[18px] tw:items-center tw:justify-center tw:rounded-[4px] tw:border tw:border-current"
        >
          <Icon icon="custom:hi-luca" class="tw:text-[14px]" />
        </span>
      </template>
      {{ t("umbrella-campaign.step-big-idea.skip-button") }}
    </Button>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
