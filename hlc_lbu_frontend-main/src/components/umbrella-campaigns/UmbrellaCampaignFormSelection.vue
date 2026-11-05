<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
} from "@/services/projects/UmbrellaCampaignsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, number, object, string } from "yup";

const { t } = useI18n();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<UmbrellaCampaignData>();

const brandId = useBrandId();
const projectId = useProjectId();
const umbrellaCampaignId = computed(() => data.value.id);

const sectionSchema = computed(() =>
  object({
    text: string().required(t("forms.required-field")).trim(),
    title: string().required(t("forms.required-field")).trim(),
  }),
);

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      preferred_umbrella_campaign: number().required(t("forms.required-field")),
      umbrella_campaigns: array()
        .of(
          object({
            id: number().required(t("forms.required-field")),
            title: string().required(t("forms.required-field")).trim(),
            sections: object().shape({
              hook: sectionSchema.value,
              message: sectionSchema.value,
              big_idea: sectionSchema.value,
            }),
            preferred: number().required(),
            description: string().required(t("forms.required-field")).trim(),
          }),
        )
        .required(),
    }),
  ),
);

const { handleSubmit, setFieldValue, values, isSubmitting, meta } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      umbrella_campaigns: data.value.umbrella_campaigns ?? undefined,
      preferred_umbrella_campaign:
        data.value.umbrella_campaigns &&
        data.value.preferred_umbrella_campaign &&
        data.value.preferred_umbrella_campaign.title ===
          data.value.umbrella_campaigns[
            data.value.preferred_umbrella_campaign.id
          ].title
          ? data.value.preferred_umbrella_campaign?.id
          : undefined,
    },
    keepValuesOnUnmount: true,
  });

const onSubmit = handleSubmit(async (values) => {
  const response1 = await UmbrellaCampaignsApi.saveGeneratedUmbrellaCampaigns(
    brandId,
    projectId,
    umbrellaCampaignId.value,
    values.umbrella_campaigns,
  );
  saveData(response1.data);

  const response2 = await UmbrellaCampaignsApi.setPreferredUmbrellaCampaign(
    brandId,
    projectId,
    umbrellaCampaignId.value,
    values.preferred_umbrella_campaign,
  );
  saveData(response2.data);

  const response3 = await UmbrellaCampaignsApi.GenerateSummary(
    brandId,
    projectId,
    umbrellaCampaignId.value,
  );
  saveData(response3.data);

  goNext();
});

const handleSelect = async (index: number) => {
  setFieldValue("preferred_umbrella_campaign", index);
  setFieldValue(`umbrella_campaigns.${index}.preferred`, 1);
  await onSubmit();
};

const regenerateCampaignList = async (text: string) => {
  if (!values.umbrella_campaigns) {
    throw new UnidentifiedError();
  }

  const response = await UmbrellaCampaignsApi.askLucaForUmbrellaCampaignList(
    brandId,
    projectId,
    umbrellaCampaignId.value,
    { text, umbrella_campaigns: values.umbrella_campaigns },
  );

  setFieldValue("umbrella_campaigns", response.data.answer);

  return response.data.answer;
};

const regenerateSingleCampaign = async (campaignId: number, text: string) => {
  if (!values.umbrella_campaigns) {
    throw new UnidentifiedError();
  }

  const value = values.umbrella_campaigns[campaignId];

  const response = await UmbrellaCampaignsApi.askLucaForOneCampaign(
    brandId,
    projectId,
    umbrellaCampaignId.value,
    { text, umbrella_campaign_selected: value },
  );

  setFieldValue(`umbrella_campaigns.${campaignId}`, {
    ...response.data.answer,
    id: value.id,
    preferred: value.preferred,
  });

  return response.data.answer;
};
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <div
      class="tw:flex tw:flex-col tw:justify-between tw:gap-4 tw:lg:flex-row tw:lg:items-center"
    >
      <PageTitle
        helpButton
        helpVideoUrl="https://www.youtube.com/watch?v=xRrOLRs2XYg"
      >
        {{ t("umbrella-campaign.step-select-umbrella-campaign.title") }}
        <template #description>
          {{ t("umbrella-campaign.step-select-umbrella-campaign.description") }}
        </template>
      </PageTitle>

      <ButtonGenerateIdea
        :fetcher="regenerateCampaignList"
        useText
        :textLabel="
          t('umbrella-campaign.step-select-umbrella-campaign.regenerate-label')
        "
        :textPlaceholder="
          t(
            'umbrella-campaign.step-select-umbrella-campaign.regenerate-placeholder',
          )
        "
        :textMaxCharacters="250"
      >
        <template #title>
          {{
            t(
              "umbrella-campaign.step-select-umbrella-campaign.regenerate-title",
            )
          }}
        </template>
        <template #description>
          {{
            t(
              "umbrella-campaign.step-select-umbrella-campaign.regenerate-description",
            )
          }}
        </template>
        <template #submit>
          {{
            t(
              "umbrella-campaign.step-select-umbrella-campaign.regenerate-submit",
            )
          }}
        </template>
      </ButtonGenerateIdea>
    </div>

    <CardGrid class="tw:items-start">
      <CardBase
        v-for="(umbrellaCampaign, index) in values.umbrella_campaigns"
        class="tw:flex tw:flex-col tw:gap-4 tw:p-6"
        :color="
          values.preferred_umbrella_campaign === umbrellaCampaign.id
            ? 'primary'
            : 'default'
        "
      >
        <FieldEditableText
          :name="`umbrella_campaigns.${index}.title`"
          required
          class="tw:mb-1 tw:text-lg tw:leading-tight tw:font-extrabold"
          variant="text"
        />

        <FieldEditableText
          :name="`umbrella_campaigns.${index}.description`"
          required
        />

        <Accordion
          :title="
            t('umbrella-campaign.step-select-umbrella-campaign.card-title')
          "
          icon="tabler-bulb"
          iconVariant="primary"
        >
          <FieldEditableText
            :name="`umbrella_campaigns.${index}.sections.big_idea.text`"
          />
        </Accordion>
        <Accordion
          :title="
            t('umbrella-campaign.step-select-umbrella-campaign.card-message')
          "
          icon="tabler-message"
          iconVariant="info"
        >
          <FieldEditableText
            :name="`umbrella_campaigns.${index}.sections.message.text`"
          />
        </Accordion>
        <Accordion
          :title="
            t('umbrella-campaign.step-select-umbrella-campaign.card-hook')
          "
          icon="tabler-magnet"
          iconVariant="error"
        >
          <FieldEditableText
            :name="`umbrella_campaigns.${index}.sections.hook.text`"
          />
        </Accordion>

        <div class="tw:flex tw:flex-col tw:gap-2">
          <Button
            class="tw:w-full"
            type="button"
            @click="handleSelect(index)"
            size="sm"
            :isLoading="
              index === values.preferred_umbrella_campaign && isSubmitting
            "
            :disabled="
              index !== values.preferred_umbrella_campaign && isSubmitting
            "
          >
            {{
              t(
                "umbrella-campaign.step-select-umbrella-campaign.select-campaign",
              )
            }}
          </Button>
          <ButtonGenerateIdea
            :fetcher="(text) => regenerateSingleCampaign(index, text)"
            useText
            color="primary"
            size="sm"
            variant="outlined"
            class="tw:bg-white"
            :textLabel="
              t(
                'umbrella-campaign.step-select-umbrella-campaign.regenerate-label',
              )
            "
            :textPlaceholder="
              t(
                'umbrella-campaign.step-select-umbrella-campaign.regenerate-single-placeholder',
              )
            "
          >
            <template #title>
              {{
                t(
                  "umbrella-campaign.step-select-umbrella-campaign.regenerate-single-title",
                )
              }}
            </template>
            <template #description>
              {{
                t(
                  "umbrella-campaign.step-select-umbrella-campaign.regenerate-single-description",
                )
              }}
            </template>
            <template #submit>
              {{
                t(
                  "umbrella-campaign.step-select-umbrella-campaign.regenerate-single-submit",
                )
              }}
            </template>
          </ButtonGenerateIdea>
        </div>
      </CardBase>
    </CardGrid>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
