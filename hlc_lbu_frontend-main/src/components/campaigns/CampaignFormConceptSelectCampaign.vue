<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, object } from "yup";
import { CampaignFormData } from "./CampaignForm.vue";
import { campaignConceptSchema } from "./schemas";
import { ref } from "vue";
import CampaignsApi from "@/services/projects/CampaignsApi";
import { LlmOutputError, UnidentifiedError } from "@/services/common-errors";

const { t } = useI18n();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<CampaignFormData>();

if (!data.value.campaigns) {
  throw new UnidentifiedError();
}

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = data.value.id;

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      campaigns: array()
        .of(campaignConceptSchema)
        .required()
        .test(
          "at-least-one-selected",
          "At least one campaign must be selected",
          (items) => {
            return items.some((item) => item.preferred === 1);
          },
        ),
    }),
  ),
);

const {
  handleSubmit,
  isSubmitting,
  setFieldValue,
  values,
  errors,
  submitCount,
  meta,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    campaigns: data.value.campaigns,
  },
  keepValuesOnUnmount: true,
});

const generalErrorMessage = ref<string>();

const onSubmit = handleSubmit(async (values) => {
  try {
    generalErrorMessage.value = undefined;

    // Save all the campaigns
    await CampaignsApi.saveGeneratedCampaigns(
      brandId,
      projectId,
      campaignId,
      values.campaigns,
    );

    // Find the selected campaign
    const campaignSelected = values.campaigns.find((c) => c.preferred === 1);
    if (!campaignSelected) {
      throw new UnidentifiedError();
    }

    // Set the selected campaign as preferred
    let response = await CampaignsApi.SetPreferredCampaign(
      brandId,
      projectId,
      campaignId,
      campaignSelected.id,
    );
    saveData(response.data);

    // Generate the summary
    response = await CampaignsApi.GenerateSummary(
      brandId,
      projectId,
      data.value.id,
    );
    saveData(response.data);

    goNext();
  } catch (error) {
    if (error instanceof LlmOutputError) {
      generalErrorMessage.value = t(`errors.${error.message}.title`);
    } else {
      throw error;
    }
  }
});

const handleChecked = (checked: boolean, index: number) => {
  if (checked) {
    // Deselect all other campaigns
    values.campaigns?.forEach((_, _index) => {
      if (index !== _index) {
        setFieldValue(`campaigns.${_index}.preferred`, 0);
      }
    });
  }
};

const expanded = ref<boolean>(false);

const askLucaFetcher = async (text: string) => {
  if (!values.campaigns) {
    throw new UnidentifiedError();
  }

  const response = await CampaignsApi.askLucaFoCampaignList(
    brandId,
    projectId,
    campaignId,
    { text, campaigns: values.campaigns },
  );

  setFieldValue("campaigns", response.data.answer);

  return response.data.answer;
};
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="concept" />
    </template>

    <div
      class="tw:flex tw:flex-col tw:justify-between tw:gap-4 tw:lg:flex-row tw:lg:items-center"
    >
      <PageTitle
        helpButton
        helpVideoUrl="https://www.youtube.com/watch?v=4VX0rxSTcog"
      >
        {{ $t("campaigns.conceptselectcampaign.title") }}
        <template #description>
          {{ $t("campaigns.conceptselectcampaign.description") }}
        </template>
      </PageTitle>

      <ButtonGenerateIdea
        :fetcher="askLucaFetcher"
        useText
        :textLabel="
          $t('campaigns.conceptselectcampaign.buttongenerateidea.textLabel')
        "
        :textPlaceholder="
          $t(
            'campaigns.conceptselectcampaign.buttongenerateidea.textPlaceholder',
          )
        "
      >
        <template #title>{{
          $t("campaigns.conceptselectcampaign.buttongenerateidea.title")
        }}</template>
        <template #description>
          {{
            $t("campaigns.conceptselectcampaign.buttongenerateidea.description")
          }}
        </template>
        <template #submit>{{
          $t("campaigns.conceptselectcampaign.buttongenerateidea.submittext")
        }}</template>
      </ButtonGenerateIdea>
    </div>
    <CardGrid>
      <CampaignFormConceptCard
        v-for="(campaign, index) in values.campaigns"
        :key="campaign.id || index"
        :name="`campaigns[${index}]`"
        @checked="handleChecked($event, index)"
        v-model:expanded="expanded"
        class="tw:grow tw:basis-0"
        :brandId="brandId"
        :projectId="projectId"
        :campaignId="campaignId"
      />
    </CardGrid>

    <Alert v-if="errors.campaigns && submitCount > 0" type="error">
      {{ errors.campaigns }}
    </Alert>

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" type="submit" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
