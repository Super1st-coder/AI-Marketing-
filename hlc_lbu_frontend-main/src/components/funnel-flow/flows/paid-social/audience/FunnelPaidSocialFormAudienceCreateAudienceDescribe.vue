<script setup lang="ts">
import { array, mixed, object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";

const { t } = useI18n();
const wizard = useFunnelPaidSocialAudienceStore();

const brandId = useBrandId();
const campaignId = useCampaignId();

const formStore = createAudienceStore();
const { createWithFileForm } = storeToRefs(formStore);

const schema = toTypedSchema(
  object({
    description: string().required(t("forms.required-field")).trim(),
    files: array()
      .of(mixed<File>().required(t("forms.required-field")))
      .required(),
  }),
);

const { handleSubmit, values, setFieldValue } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    description: createWithFileForm.value.description || "",
    files: createWithFileForm.value.files || [],
  },
});

watch(
  () => ({ ...values }),
  (newValues) => {
    formStore.saveFileFormProgress({
      description: newValues.description,
      files: newValues.files,
    });
  },
  { deep: true },
);

const onSubmit = handleSubmit(async (values) => {
  wizard.setStep("GENERATE_AUD_LOADER");

  if (values.files.length > 0) {
    await wizard.generateAudiencesFromDescriptionOrFile({
      campaign_id: campaignId,
      brand_id: brandId,
      ad_set_id: wizard.selectedAdSet.id,
      files: values.files,
    });
  } else {
    await wizard.generateAudiencesFromDescriptionOrFile({
      campaign_id: campaignId,
      brand_id: brandId,
      ad_set_id: wizard.selectedAdSet.id,
      description: values.description,
    });
  }

  formStore.resetFileForm();
  setFieldValue("description", "", false);
  setFieldValue("files", [], false);

  wizard.setStep("GENERATED_AUDIENCE");
});

const disableTextarea = computed(() => values.files && values.files.length > 0);

watch(
  () => values.files,
  (files) => {
    if (files) {
      if (files.length === 0) {
        setFieldValue("description", "", false);
      } else {
        setFieldValue(
          "description",
          t(
            "funnel-flow.paid-social.audience.create-audience-describe.auto-description-with-attachments",
          ),
        );
      }
    }
  },
);
</script>

<template>
  <form @submit.prevent="onSubmit" class="tw:flex tw:flex-col tw:gap-6">
    <FieldTextareaWithAttachments
      name="description"
      :label="
        $t('funnel-flow.paid-social.audience.create-audience-describe.label')
      "
      :placeholder="
        $t(
          'funnel-flow.paid-social.audience.create-audience-describe.placeholder',
        )
      "
      attachmentsName="files"
      multipleAttachments
      :disabled="disableTextarea"
    />

    <Separator />

    <div class="tw:flex tw:justify-end tw:gap-4">
      <Button
        @click="wizard.setStep('START')"
        size="md"
        variant="outlined"
        type="button"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button size="md" type="submit">
        {{ $t("audience.ai-research.create-audience.create-audience-btn") }}
      </Button>
    </div>
  </form>
</template>
