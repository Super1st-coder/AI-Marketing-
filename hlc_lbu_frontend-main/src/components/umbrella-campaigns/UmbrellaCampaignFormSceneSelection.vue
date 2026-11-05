<script setup lang="ts">
import { object, array, string, number } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import UmbrellaCampaignFormSceneSelectionCards from "./UmbrellaCampaignFormSceneSelectionCards.vue";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
  UmbrellaCampaignStoryStage,
  UmbrellaCampaignStoryStageItem,
} from "@/services/projects/UmbrellaCampaignsApi";
import { UnidentifiedError } from "@/services/common-errors";
import draggable from "vuedraggable";

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<UmbrellaCampaignData>();
const brandId = useBrandId();
const projectId = useProjectId();
const { t } = useI18n();
const schema = computed(() =>
  toTypedSchema(
    object({
      selected_stages_ids: array()
        .of(number().required())
        .min(
          1,
          t("umbrella-campaign.step-scene.select-scene.no-stages-message"),
        )
        .required(
          t("umbrella-campaign.step-scene.select-scene.select-stages-title"),
        ),
      story_plot: string().required(t("forms.required-field")).trim(),
      scene_reasoning: string().required(t("forms.required-field")).trim(),
      scenes: array()
        .of(
          object({
            id: number().required(),
            title: string().required(t("forms.required-field")),
            text: string().required(t("forms.required-field")).trim(),
            preferred: number().required(),
          }),
        )
        .required(),
      preferred_scene: number().required(t("forms.required-field")),
    }),
  ),
);

const {
  handleSubmit,
  isSubmitting,
  values,
  errors,
  setFieldValue,
  validateField,
  scrollToFirstError,
  meta,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    selected_stages_ids: data.value.story_stages?.map((stage) => stage.id),
    story_plot: data.value.story_plot ?? undefined,
    scene_reasoning: data.value.scene_reasoning ?? undefined,
    scenes: data.value.scenes ?? undefined,
    preferred_scene: data.value.preferred_scene?.id ?? undefined,
  },
});

const isInfoAvailable = ref(
  (data.value.scene_reasoning?.trim?.().length ?? 0) > 0 &&
    (data.value.story_plot?.trim?.().length ?? 0) > 0
    ? true
    : false,
);
const umbrellaCampaignId = computed(() => data.value.id);

const sortableStoryStages = ref<UmbrellaCampaignStoryStage[]>(
  data.value.story_stages ?? [],
);

const sortedSelectedStages = computed(() =>
  sortableStoryStages.value.filter((stage) =>
    values.selected_stages_ids?.includes(stage.id),
  ),
);

const handleCardToggle = (stageItem: UmbrellaCampaignStoryStageItem) => {
  let newIds = [...(values.selected_stages_ids ?? [])];

  if (newIds.includes(stageItem.id)) {
    newIds = newIds.filter((id) => id !== stageItem.id);
  } else {
    newIds.push(stageItem.id);
  }

  setFieldValue("selected_stages_ids", newIds);
};

const handleGeneratePlot = async () => {
  const { valid: areSelectedStagesValid } = await validateField(
    "selected_stages_ids",
  );

  if (!areSelectedStagesValid) {
    await scrollToFirstError();
    return;
  }

  // Generate plot
  const response =
    await UmbrellaCampaignsApi.GenerateStoryPlotByUmbrellaCampaign(
      brandId,
      projectId,
      data.value.id,
      {
        stages_selected: sortedSelectedStages.value,
      },
    );

  // Save data
  setFieldValue("story_plot", response.data.answer.story_plot);
  setFieldValue("scene_reasoning", response.data.answer.scene_reasoning);

  isInfoAvailable.value = true;
};

const onSubmit = handleSubmit(async (values) => {
  //Save Scenes
  const response1 =
    await UmbrellaCampaignsApi.SaveGeneratedScenesBymbrellaCampaign(
      brandId,
      projectId,
      umbrellaCampaignId.value,
      {
        stages_selected: sortedSelectedStages.value,
        story_plot: values.story_plot,
        scene_reasoning: values.scene_reasoning,
        scenes: values.scenes,
      },
    );
  saveData(response1.data);

  // Save preferred scene
  const response2 =
    await UmbrellaCampaignsApi.SettingPreferredSceneByUmbrellaCampaign(
      brandId,
      projectId,
      umbrellaCampaignId.value,
      {
        preferred_scene_id: values.preferred_scene,
      },
    );
  saveData(response2.data);

  // generate Ummbrella Campaign
  const response3 = await UmbrellaCampaignsApi.GenerateUmbrellaCampaigns(
    brandId,
    projectId,
    umbrellaCampaignId.value,
  );
  saveData(response3.data);

  goNext();
});

const areScenesAvailable = ref(!!data.value.scenes);

const getCommonParametersForGeneration = async () => {
  const { valid: areSelectedStagesValid } = await validateField(
    "selected_stages_ids",
  );
  const { valid: isStoryplotValid } = await validateField("story_plot");
  const { valid: isSceneReasoningValid } =
    await validateField("scene_reasoning");

  // Check needed fields
  if (!areSelectedStagesValid || !isStoryplotValid || !isSceneReasoningValid) {
    await scrollToFirstError();
    return;
  }

  if (!values.story_plot || !values.scene_reasoning) {
    throw new UnidentifiedError();
  }

  return {
    stages_selected: sortedSelectedStages.value,
    story_plot: values.story_plot,
    scene_reasoning: values.scene_reasoning,
  };
};

const handleClickGenerateScenes = async () => {
  const commonParameters = await getCommonParametersForGeneration();
  if (!commonParameters) {
    return;
  }

  // Generate data
  const response = await UmbrellaCampaignsApi.GenerateScenesByUmbrellaCampaign(
    brandId,
    projectId,
    data.value.id,
    {
      ...commonParameters,
    },
  );

  setFieldValue("scenes", response.data.answer);
  setFieldValue("preferred_scene", undefined);

  areScenesAvailable.value = true;
};

const handleSelect = async (index: number) => {
  setFieldValue("preferred_scene", index);
  setFieldValue(`scenes.${index}.preferred`, 1);
  await onSubmit();
};

const regenerateSceneList = async (text: string) => {
  const commonParameters = await getCommonParametersForGeneration();
  if (!commonParameters) {
    return;
  }

  if (!values.scenes) {
    throw new UnidentifiedError();
  }

  const response =
    await UmbrellaCampaignsApi.AskLucaForScenesByUmbrellaCampaign(
      brandId,
      projectId,
      umbrellaCampaignId.value,
      {
        ...commonParameters,
        text: text,
        scenes: values.scenes,
      },
    );

  setFieldValue("scenes", response.data.answer);

  return response.data.answer;
};

const regenerateSingleScene = async (sceneId: number, text: string) => {
  const commonParameters = await getCommonParametersForGeneration();
  if (!commonParameters) {
    return;
  }

  if (!values.scenes) {
    throw new UnidentifiedError();
  }

  const value = values.scenes[sceneId];

  const response =
    await UmbrellaCampaignsApi.AskLucaForaSceneByUmbrellaCampaign(
      brandId,
      projectId,
      umbrellaCampaignId.value,
      {
        ...commonParameters,
        text: text,
        scene_selected: value,
      },
    );

  setFieldValue(`scenes.${sceneId}`, {
    ...response.data.answer,
    id: value.id,
    preferred: value.preferred,
  });

  return response.data.answer;
};
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="scene" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=h3RLoihDatg"
    >
      {{ t("umbrella-campaign.step-scene.select-scene.title") }}
      <template #description>
        {{ t("umbrella-campaign.step-scene.select-scene.description") }}
      </template>
    </PageTitle>

    <h2 class="tw:mb-6 tw:text-base tw:font-bold tw:text-primary-text">
      {{ t("umbrella-campaign.step-scene.select-scene.select-stages-title") }}
    </h2>

    <!-- Stage Selection Cards  -->
    <draggable
      v-model="sortableStoryStages"
      :options="{ animation: 200, direction: 'horizontal' }"
      item-key="name"
      class="tw:flex tw:flex-col tw:justify-start tw:gap-6 tw:xl:flex-row tw:xl:flex-wrap tw:xl:first-letter:items-center"
    >
      <template #item="{ element }">
        <UmbrellaCampaignFormSceneSelectionCards
          :stage-item="element"
          :selected="values.selected_stages_ids?.includes(element.id)"
          class="tw:grow tw:basis-0"
          style="max-width: 500px"
          @toggle="handleCardToggle(element)"
        />
      </template>
    </draggable>

    <FieldError>
      {{ errors.selected_stages_ids }}
    </FieldError>

    <div class="tw:w-fit">
      <ButtonRegenerate
        :regenerate="isInfoAvailable"
        :fetcher="handleGeneratePlot"
      >
        <template #generate>
          {{ $t("umbrella-campaign.step-scene.select-scene.button-generate") }}
        </template>

        <template #regenerate>
          {{
            $t("umbrella-campaign.step-scene.select-scene.button-regenerate")
          }}
        </template>
      </ButtonRegenerate>
    </div>

    <template v-if="isInfoAvailable">
      <Separator />
      <CardBase class="tw:flex tw:flex-col tw:gap-5 tw:p-4">
        <CardTitle>{{
          t("umbrella-campaign.step-scene.select-scene.story-plot-title")
        }}</CardTitle>
        <FieldTextarea name="story_plot" required />
      </CardBase>
      <CardBase class="tw:flex tw:flex-col tw:gap-5 tw:p-4">
        <CardTitle>{{
          t("umbrella-campaign.step-scene.select-scene.reasoning-title")
        }}</CardTitle>
        <FieldTextarea name="scene_reasoning" required />
      </CardBase>

      <div class="tw:w-fit">
        <ButtonRegenerate
          :regenerate="areScenesAvailable"
          :fetcher="handleClickGenerateScenes"
        >
          <template #generate>
            {{
              $t(
                "umbrella-campaign.step-scene.select-scene.button-generate-scene",
              )
            }}
          </template>

          <template #regenerate>
            {{
              $t(
                "umbrella-campaign.step-scene.select-scene.button-regenerate-scene",
              )
            }}
          </template>
        </ButtonRegenerate>
      </div>
    </template>

    <template v-if="areScenesAvailable">
      <Separator />
      <div
        class="tw:flex tw:flex-col tw:justify-between tw:gap-4 tw:lg:flex-row tw:lg:items-center"
      >
        <CardTitle iconVariant="gray" icon="tabler:frame">
          {{
            t("umbrella-campaign.step-scene.select-scene.stages-frames-title")
          }}
        </CardTitle>
        <ButtonGenerateIdea
          :fetcher="regenerateSceneList"
          useText
          textLabel=""
          :textPlaceholder="
            t('umbrella-campaign.step-scene.select-scene.overwrite-description')
          "
          :textMaxCharacters="250"
        >
          <template #title>
            {{ t("umbrella-campaign.step-scene.select-scene.overwrite-title") }}
          </template>
          <template #description>
            {{
              t(
                "umbrella-campaign.step-scene.select-scene.overwrite-description",
              )
            }}
          </template>
          <template #submit>
            {{
              t("umbrella-campaign.step-scene.select-scene.overwrite-submit")
            }}
          </template>
        </ButtonGenerateIdea>
      </div>
      <CardGrid>
        <CardBase
          v-for="(scene, index) in values.scenes"
          class="tw:flex tw:flex-col tw:gap-4 tw:p-6"
          :color="values.preferred_scene === scene.id ? 'primary' : 'default'"
        >
          <FieldEditableText
            :name="`scenes.${index}.title`"
            required
            class="tw:mb-1 tw:text-lg tw:leading-tight tw:font-extrabold"
            variant="text"
          />
          <FieldEditableText :name="`scenes.${index}.text`" required />
          <div class="tw:flex tw:flex-col tw:gap-2">
            <ButtonGenerateIdea
              :fetcher="(text) => regenerateSingleScene(index, text)"
              useText
              color="primary"
              size="sm"
              variant="outlined"
              class="tw:bg-white"
              textLabel=""
              :textPlaceholder="
                t(
                  'umbrella-campaign.step-scene.select-scene.refine-description',
                )
              "
            >
              <template #title>
                {{
                  t("umbrella-campaign.step-scene.select-scene.refine-title")
                }}
              </template>
              <template #description>
                {{
                  t(
                    "umbrella-campaign.step-scene.select-scene.refine-description",
                  )
                }}
              </template>
              <template #submit>
                {{
                  t("umbrella-campaign.step-scene.select-scene.refine-submit")
                }}
              </template>
            </ButtonGenerateIdea>
            <Button
              class="tw:w-full"
              type="button"
              @click="handleSelect(index)"
              size="sm"
              :isLoading="index === values.preferred_scene && isSubmitting"
              :disabled="index !== values.preferred_scene && isSubmitting"
            >
              {{ t("umbrella-campaign.step-scene.select-scene.select-scene") }}
            </Button>
          </div>
        </CardBase>
      </CardGrid>
    </template>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
