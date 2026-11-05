<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
} from "@/services/projects/UmbrellaCampaignsApi";
import UtilsApi from "@/services/UtilsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, object, string } from "yup";

const { t } = useI18n();

const brandId = useBrandId();
const projectId = useProjectId();
const umbrellaCampaignId = computed(() => data.value.id);

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<UmbrellaCampaignData>();

const { data: resourceList } = await UtilsApi.getUmbrellaResourceList();

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      resources: array()
        .of(
          object({
            name: string().required(t("forms.required-field")),
            display_name: string().required(t("forms.required-field")),
            description: string().required(t("forms.required-field")),
            text: string().required(t("forms.required-field")).trim(),
            label: string().required(t("forms.required-field")),
          }),
        )
        .required(),
    }),
  ),
);

const { handleSubmit, isSubmitting, values, setFieldValue, meta } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      resources:
        data.value.bperson_resources ??
        resourceList.map((resource) => ({ ...resource, text: "", label: "" })),
    },
  });

const onSubmit = handleSubmit(async (values) => {
  const response = await UmbrellaCampaignsApi.setBuyerPersonResources(
    brandId,
    projectId,
    data.value.id,
    values.resources,
  );

  saveData(response.data);
  goNext();
});

const { confirm, handleValue } = useConfirmModal<"missingOnly" | "all">(
  "giveMeIdeas",
);

const handleGenerateIdeas = async () => {
  if (!values.resources) {
    throw new UnidentifiedError();
  }

  // Check if there is any answer
  const anyAnswer = values.resources.some(
    (resource) => resource.text.trim() !== "",
  );

  // Show confirm modal if there is any answer
  const result = anyAnswer ? await confirm() : "all";

  // Closed
  if (result === "close") {
    return;
  }

  const { data: generated } =
    await UmbrellaCampaignsApi.askLucaForBuyerResources(
      brandId,
      projectId,
      umbrellaCampaignId.value,
    );

  for (const name in generated.answer) {
    const index = values.resources.findIndex((item) => item.name === name);

    if (index !== -1) {
      const answer = generated.answer[name];
      const currentAnswer = values.resources[index].text.trim();
      if (
        result === "all" ||
        (result === "missingOnly" && currentAnswer === "")
      ) {
        setFieldValue(`resources.${index}.text`, answer.text);
        setFieldValue(`resources.${index}.label`, answer.label);
      }
    }
  }
};
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="benefit" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=HUAj5DwpfsA"
    >
      {{ t("umbrella-campaign.step-benefit.resources.title") }}
      <template #description>
        {{ t("umbrella-campaign.step-benefit.resources.description") }}
      </template>
    </PageTitle>

    <div class="tw:flex tw:justify-end">
      <ButtonGenerateIdea :fetcher="handleGenerateIdeas">
        {{ $t("forms.give-me-ideas.button") }}
      </ButtonGenerateIdea>
    </div>

    <CardGrid class="tw:items-start">
      <UmbrellaCampaignFormBenefitResourceCard
        v-for="(_resource, index) in values.resources"
        :key="index"
        :name="`resources[${index}]`"
      />
    </CardGrid>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />

    <!-- Generate ideas -->
    <ModalConfirmGeneric name="giveMeIdeas">
      <template #title>
        {{ t("umbrella-campaign.ask-luca-modal.title") }}
      </template>

      <template #description>
        {{ t("umbrella-campaign.ask-luca-modal.description") }}
      </template>

      <template #actions>
        <Button
          size="md"
          variant="outlined"
          type="button"
          @click="handleValue('all')"
        >
          {{ t("umbrella-campaign.ask-luca-modal.replace-all") }}
        </Button>

        <Button size="md" type="button" @click="handleValue('missingOnly')">
          {{ t("umbrella-campaign.ask-luca-modal.missing-only") }}
        </Button>
      </template>
    </ModalConfirmGeneric>
  </FormStepLayout>
</template>
