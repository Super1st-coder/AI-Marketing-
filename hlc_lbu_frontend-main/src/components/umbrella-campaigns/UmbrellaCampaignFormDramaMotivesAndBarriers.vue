<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
} from "@/services/projects/UmbrellaCampaignsApi";
import UtilsApi from "@/services/UtilsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, object, string } from "yup";

const { t } = useI18n();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<UmbrellaCampaignData>();

const brandId = useBrandId();
const projectId = useProjectId();
const umbrellaCampaignId = computed(() => data.value.id);

const { data: motiveAndBarrierList } =
  await UtilsApi.getUmbrellaMotiveAndBarrierList();

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      bperson_motives: array()
        .of(
          object({
            name: string().required(t("forms.required-field")),
            display_name: string().required(t("forms.required-field")),
            description: string().required(t("forms.required-field")),
            text: string().required(t("forms.required-field")).trim(),
          }),
        )
        .required(),
      bperson_barriers: array()
        .of(
          object({
            name: string().required(t("forms.required-field")),
            display_name: string().required(t("forms.required-field")),
            description: string().required(t("forms.required-field")),
            text: string().required(t("forms.required-field")).trim(),
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
      bperson_motives:
        data.value.bperson_motives ??
        motiveAndBarrierList.motives.map((resource) => ({
          ...resource,
          text: "",
        })),
      bperson_barriers:
        data.value.bperson_barriers ??
        motiveAndBarrierList.barriers.map((resource) => ({
          ...resource,
          text: "",
        })),
    },
  });

const onSubmit = handleSubmit(async (values) => {
  const response = await UmbrellaCampaignsApi.setBuyerPersonMotivesAndBarriers(
    brandId,
    projectId,
    data.value.id,
    {
      bperson_barriers: values.bperson_barriers,
      bperson_motives: values.bperson_motives,
    },
  );

  saveData(response.data);
  goNext();
});

const { confirm, handleValue } = useConfirmModal<"missingOnly" | "all">(
  "giveMeIdeas",
);

const handleGenerateIdeas = async () => {
  if (!values.bperson_motives || !values.bperson_barriers) {
    throw new UnidentifiedError();
  }

  // Check if there is any answer
  const anyAnswer =
    values.bperson_motives.some((resource) => resource.text.trim() !== "") ||
    values.bperson_barriers.some((resource) => resource.text.trim() !== "");

  // Show confirm modal if there is any answer
  const result = anyAnswer ? await confirm() : "all";

  // Closed
  if (result === "close") {
    return;
  }

  const { data: generated } =
    await UmbrellaCampaignsApi.askLucaForBuyerPersonMotivesAndBarriers(
      brandId,
      projectId,
      umbrellaCampaignId.value,
    );

  for (const name in generated.answer.barriers) {
    const index = values.bperson_barriers.findIndex(
      (item) => item.name === name,
    );

    if (index !== -1) {
      const newAnswer = generated.answer.barriers[name];
      const currentAnswer = values.bperson_barriers[index].text.trim();
      if (
        result === "all" ||
        (result === "missingOnly" && currentAnswer === "")
      ) {
        setFieldValue(`bperson_barriers.${index}.text`, newAnswer.text);
      }
    }
  }

  for (const name in generated.answer.motives) {
    const index = values.bperson_motives.findIndex(
      (item) => item.name === name,
    );

    if (index !== -1) {
      const newAnswer = generated.answer.motives[name];
      const currentAnswer = values.bperson_motives[index].text.trim();
      if (
        result === "all" ||
        (result === "missingOnly" && currentAnswer === "")
      ) {
        setFieldValue(`bperson_motives.${index}.text`, newAnswer.text);
      }
    }
  }

  return generated;
};
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="drama" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=ghWYiqbDw9k"
    >
      {{ t("umbrella-campaign.step-drama.motives-and-barriers.title") }}
      <template #description>
        {{ t("umbrella-campaign.step-drama.motives-and-barriers.description") }}
      </template>
    </PageTitle>

    <div class="tw:flex tw:justify-end">
      <ButtonGenerateIdea :fetcher="handleGenerateIdeas">
        {{ $t("forms.give-me-ideas.button") }}
      </ButtonGenerateIdea>
    </div>

    <div class="tw:grid tw:gap-6 tw:lg:grid-cols-2">
      <template
        v-for="(_resource, index) in values.bperson_motives"
        :key="index"
      >
        <!-- Left: Motive -->
        <UmbrellaCampaignFormDramaMotivesAndBarriersCard
          :name="`bperson_motives[${index}]`"
        />
        <!-- Right: Barrier -->
        <UmbrellaCampaignFormDramaMotivesAndBarriersCard
          :name="`bperson_barriers[${index}]`"
        />
      </template>
    </div>

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
