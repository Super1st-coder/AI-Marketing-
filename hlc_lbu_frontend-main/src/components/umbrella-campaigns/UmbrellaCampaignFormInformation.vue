<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { useI18n } from "vue-i18n";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
  UmbrellaCampaignResponse,
} from "@/services/projects/UmbrellaCampaignsApi";

const appLocaleData = useAppLocaleData();
const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const brandId = useBrandId();
const projectId = useProjectId();

const { goNext, data, saveData } = useMultiStepFormContext<
  UmbrellaCampaignData | undefined
>();

const schema = computed(() =>
  toTypedSchema(
    object({
      name: string()
        .required(t("forms.required-field"))
        .max(100, ({ max }) => t("forms.max-characters", { max }))
        .trim(),
      context: string()
        .required(t("forms.required-field"))
        .max(500, ({ max }) => t("forms.max-characters", { max }))
        .trim(),
      target_regions: string()
        .required(t("forms.required-field"))
        .max(500, ({ max }) => t("forms.max-characters", { max }))
        .trim(),
      language: string().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    name: data.value?.name,
    context: data.value?.context,
    target_regions: data.value?.target_regions,
    language: data.value?.language ?? appLocaleData.value.apiName ?? undefined,
  },
});

const disableSaveAlert = ref(false);

const onSubmit = handleSubmit(async (values) => {
  let response: UmbrellaCampaignResponse;
  if (data.value?.id) {
    // Update existing brand
    response = await UmbrellaCampaignsApi.update(
      brandId,
      projectId,
      data.value.id,
      values,
    );
  } else {
    // Create brand and save data
    response = await UmbrellaCampaignsApi.create(brandId, projectId, values);
  }

  if (data.value?.id) {
    // Go to the next step
    saveData({
      ...response.data,
    });
    goNext();
  } else {
    // Go to the settings page
    disableSaveAlert.value = true;
    await router.replace({
      name: "UmbrellaCampaignSettings",
      params: { umbrellaCampaignId: response.data.id },
      query: route.query,
      hash: route.hash,
    });
  }
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=EdvQY3LG3SI"
    >
      {{ t("umbrella-campaign.step-information.title") }}
      <template #description>
        {{ t("umbrella-campaign.step-information.description") }}
      </template>
    </PageTitle>

    <FieldsContainer class="tw:grow">
      <FieldTextarea
        name="name"
        :label="t('umbrella-campaign.step-information.name.label')"
        :placeholder="t('umbrella-campaign.step-information.name.placeholder')"
        :maxCharacters="100"
        :rows="1"
        required
        speechRecognition
      />

      <FieldTextarea
        name="context"
        :label="t('umbrella-campaign.step-information.context.label')"
        :placeholder="
          t('umbrella-campaign.step-information.context.placeholder')
        "
        :maxCharacters="500"
        required
        speechRecognition
      />

      <FieldTextarea
        name="target_regions"
        :label="t('umbrella-campaign.step-information.target_regions.label')"
        :placeholder="
          t('umbrella-campaign.step-information.target_regions.placeholder')
        "
        :maxCharacters="500"
        required
        speechRecognition
      />

      <FieldLanguage
        name="language"
        :label="t('umbrella-campaign.step-information.language.label')"
        :placeholder="
          t('umbrella-campaign.step-information.language.placeholder')
        "
        required
      />
    </FieldsContainer>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack :to="{ name: 'CampaignList' }" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />
  </FormStepLayout>
</template>
