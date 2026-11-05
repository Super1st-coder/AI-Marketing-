<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import { useI18n } from "vue-i18n";
import { CampaignFormData } from "./CampaignForm.vue";
import CampaignsApi, {
  CampaignResponse,
} from "@/services/projects/CampaignsApi";

const appLocaleData = useAppLocaleData();
const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const brandId = useBrandId();
const projectId = useProjectId();

const { goNext, data, saveData } = useMultiStepFormContext<
  CampaignFormData | undefined
>();

const schema = computed(() =>
  toTypedSchema(
    object({
      language: string().required(t("forms.required-field")),
      name: string().required(t("forms.required-field")).trim(),
      description: string().required(t("forms.required-field")).trim(),
      target_regions: string().required(t("forms.required-field")).trim(),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    language: data.value?.language ?? appLocaleData.value.apiName ?? undefined,
    name: data.value?.name,
    description: data.value?.description,
    target_regions: data.value?.target_regions,
  },
});

const disableSaveAlert = ref(false);

const onSubmit = handleSubmit(async (values) => {
  let response: CampaignResponse;
  if (data.value?.id) {
    // Update existing brand
    response = await CampaignsApi.update(
      brandId,
      projectId,
      data.value.id,
      values,
    );
  } else {
    // Create brand and save data
    response = await CampaignsApi.create(brandId, projectId, values);
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
      name: "CampaignSettings",
      params: { campaignId: response.data.id },
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
      helpVideoUrl="https://www.youtube.com/watch?v=8gABvZ2EbGo"
    >
      {{ $t("campaigns.information.title") }}
      <template #description>
        {{ $t("campaigns.information.subtitle") }}
      </template>
    </PageTitle>

    <FieldsContainer class="tw:grow">
      <FieldTextarea
        name="name"
        :label="$t('campaigns.information.name.label')"
        :placeholder="$t('campaigns.information.name.placeholder')"
        required
        :rows="1"
      />

      <FieldLanguage
        name="language"
        :label="$t('campaigns.information.language.label')"
        :placeholder="$t('campaigns.information.language.placeholder')"
        required
      />

      <FieldTextarea
        name="target_regions"
        :label="$t('campaigns.information.region.label')"
        :placeholder="$t('campaigns.information.region.placeholder')"
        required
        speechRecognition
      />

      <FieldTextarea
        name="description"
        :label="$t('campaigns.information.cconceptdetail.label')"
        :placeholder="$t('campaigns.information.cconceptdetail.placeholder')"
        required
        speechRecognition
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
