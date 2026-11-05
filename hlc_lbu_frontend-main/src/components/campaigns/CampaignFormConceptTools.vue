<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { CampaignFormData } from "./CampaignForm.vue";
import CampaignsApi from "@/services/projects/CampaignsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<CampaignFormData>();

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      tools: string().trim().required(t("forms.required-field")).trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, defineField, meta } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      tools: data.value.tools ?? undefined,
    },
  });

const onSubmit = handleSubmit(async (values) => {
  let response = await CampaignsApi.setTools(
    brandId,
    projectId,
    data.value.id,
    values.tools,
  );

  // Save data and go next
  saveData({
    ...response.data,
  });
  goNext();
});

const fetchAskLuca = async (text: string) => {
  const response = await CampaignsApi.askLucaByStep(
    brandId,
    projectId,
    data.value?.id,
    9,
    text,
  );

  return response.data.answer;
};

const [text] = defineField("tools");
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
      {{ $t("campaigns.concepttool.title") }}
      <template #description>
        {{ $t("campaigns.concepttool.description") }}
      </template>
    </PageTitle>

    <FieldsContainer>
      <FieldTextarea
        name="tools"
        :placeholder="$t('campaigns.concepttool.inputplaceholder')"
        speechRecognition
        required
      />
    </FieldsContainer>

    <ButtonGenerateIdeaList v-model="text" :fetcher="fetchAskLuca" />

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
