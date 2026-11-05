<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
} from "@/services/projects/UmbrellaCampaignsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, number, object, string } from "yup";

const { t } = useI18n();

const brandId = useBrandId();
const projectId = useProjectId();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<UmbrellaCampaignData>();

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      selected_motive: string().required(t("forms.required-field")),
      selected_barrier: string().required(t("forms.required-field")),

      emotional_tension_title: string()
        .required(t("forms.required-field"))
        .trim(),
      emotional_tension_text: string()
        .required(t("forms.required-field"))
        .trim(),

      drama_reasoning: string().required(t("forms.required-field")).trim(),

      preferred_drama: number().required(t("forms.required-field")),
      dramas: array()
        .of(
          object({
            id: number().required(),
            title: string().required(t("forms.required-field")),
            text: string().required(t("forms.required-field")).trim(),
            preferred: number().required(),
          }),
        )
        .required(),
    }),
  ),
);

const {
  handleSubmit,
  validateField,
  setFieldValue,
  scrollToFirstError,
  values,
  isSubmitting,
  meta,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    selected_motive: data.value.bperson_motive_selected?.name,
    selected_barrier: data.value.bperson_barrier_selected?.name,
    emotional_tension_title: data.value.emotional_tension?.title,
    emotional_tension_text: data.value.emotional_tension?.text,
    drama_reasoning: data.value.drama_reasoning ?? undefined,
    dramas: data.value.dramas ?? undefined,
    preferred_drama: data.value.preferred_drama?.id,
  },
});

const onSubmit = handleSubmit(async (values) => {
  const bperson_motive_selected = data.value.bperson_motives?.find(
    (motive) => motive.name === values.selected_motive,
  );
  const bperson_barrier_selected = data.value.bperson_barriers?.find(
    (barrier) => barrier.name === values.selected_barrier,
  );

  if (!bperson_motive_selected || !bperson_barrier_selected) {
    throw new UnidentifiedError();
  }

  const response1 = await UmbrellaCampaignsApi.saveGeneratedDramas(
    brandId,
    projectId,
    data.value.id,
    {
      bperson_motive_selected,
      bperson_barrier_selected,
      emotional_tension: {
        title: values.emotional_tension_title,
        text: values.emotional_tension_text,
      },
      drama_reasoning: values.drama_reasoning,
      dramas: values.dramas,
    },
  );
  saveData(response1.data);

  const response2 = await UmbrellaCampaignsApi.setPreferredDrama(
    brandId,
    projectId,
    data.value.id,
    values.preferred_drama,
  );
  saveData(response2.data);

  goNext();
});

const isInfoAvailable = ref(
  data.value.emotional_tension?.title &&
    data.value.emotional_tension?.text &&
    data.value.drama_reasoning
    ? true
    : false,
);

const handleClickGenerate = async () => {
  const { valid: isMotiveValid } = await validateField("selected_motive");
  const { valid: isBarrierValid } = await validateField("selected_barrier");

  if (!isMotiveValid || !isBarrierValid) {
    await scrollToFirstError();
    return;
  }

  const bperson_motive_selected = data.value.bperson_motives?.find(
    (motive) => motive.name === values.selected_motive,
  );
  const bperson_barrier_selected = data.value.bperson_barriers?.find(
    (barrier) => barrier.name === values.selected_barrier,
  );

  if (!bperson_motive_selected || !bperson_barrier_selected) {
    throw new UnidentifiedError();
  }

  // Generate data
  const response = await UmbrellaCampaignsApi.generateEmotionalTension(
    brandId,
    projectId,
    data.value.id,
    {
      bperson_motive_selected,
      bperson_barrier_selected,
    },
  );

  // Save data
  setFieldValue(
    "emotional_tension_title",
    response.data.answer.emotional_tension.title,
  );
  setFieldValue(
    "emotional_tension_text",
    response.data.answer.emotional_tension.text,
  );
  setFieldValue("drama_reasoning", response.data.answer.drama_reasoning);

  isInfoAvailable.value = true;
};

const areDramasAvailable = ref(!!data.value.dramas);

const getCommonParametersForGeneration = async () => {
  const { valid: isMotiveValid } = await validateField("selected_motive");
  const { valid: isBarrierValid } = await validateField("selected_barrier");
  const { valid: isTensionTitleValid } = await validateField(
    "emotional_tension_title",
  );
  const { valid: isTensionTextValid } = await validateField(
    "emotional_tension_text",
  );
  const { valid: isDramaReasoningValid } =
    await validateField("drama_reasoning");

  // Check needed fields
  if (
    !isMotiveValid ||
    !isBarrierValid ||
    !isTensionTitleValid ||
    !isTensionTextValid ||
    !isDramaReasoningValid
  ) {
    await scrollToFirstError();
    return;
  }

  const bperson_motive_selected = data.value.bperson_motives?.find(
    (motive) => motive.name === values.selected_motive,
  );
  const bperson_barrier_selected = data.value.bperson_barriers?.find(
    (barrier) => barrier.name === values.selected_barrier,
  );

  if (
    !values.drama_reasoning ||
    !values.emotional_tension_title ||
    !values.emotional_tension_text ||
    !bperson_motive_selected ||
    !bperson_barrier_selected
  ) {
    throw new UnidentifiedError();
  }

  // Generate data
  return {
    bperson_motive_selected,
    bperson_barrier_selected,
    emotional_tension: {
      title: values.emotional_tension_title,
      text: values.emotional_tension_text,
    },
    drama_reasoning: values.drama_reasoning,
  };
};

const handleClickGenerateDramas = async () => {
  const commonParameters = await getCommonParametersForGeneration();
  if (!commonParameters) {
    return;
  }

  // Generate data
  const response = await UmbrellaCampaignsApi.generateDramas(
    brandId,
    projectId,
    data.value.id,
    {
      ...commonParameters,
    },
  );

  // Save data
  setFieldValue("dramas", response.data.answer);
  setFieldValue("preferred_drama", undefined);

  areDramasAvailable.value = true;
};

const handleSelect = async (index: number) => {
  setFieldValue("preferred_drama", index);
  setFieldValue(`dramas.${index}.preferred`, 1);
  // await onSubmit();
};

const regenerateDramaList = async (text: string) => {
  const commonParameters = await getCommonParametersForGeneration();
  if (!commonParameters) {
    return;
  }

  const response = await UmbrellaCampaignsApi.askLucaForDramas(
    brandId,
    projectId,
    data.value.id,
    { text, ...commonParameters },
  );

  setFieldValue("dramas", response.data.answer);
  setFieldValue("preferred_drama", undefined);

  return response.data.answer;
};

const regenerateSingleDrama = (index: number) => {
  return async (text: string) => {
    const commonParameters = await getCommonParametersForGeneration();
    if (!commonParameters) {
      return;
    }

    const currentDrama = values.dramas?.[index];
    if (!currentDrama) return;

    const response = await UmbrellaCampaignsApi.askLucaForOneDrama(
      brandId,
      projectId,
      data.value.id,
      {
        text,
        drama_selected: currentDrama,
        ...commonParameters,
      },
    );

    setFieldValue(`dramas.${index}`, response.data.answer);

    return response.data.answer;
  };
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
      {{ $t("umbrella-campaign.step-drama.drama-selection.title") }}

      <template #description>
        {{ $t("umbrella-campaign.step-drama.drama-selection.description-1")
        }}<br /><br />
        {{ $t("umbrella-campaign.step-drama.drama-selection.description-2")
        }}<br /><br />
        <strong>{{
          $t("umbrella-campaign.step-drama.drama-selection.description-3")
        }}</strong>
      </template>
    </PageTitle>

    <div class="tw:flex tw:flex-col tw:gap-7 tw:md:flex-row">
      <FieldSelect
        name="selected_motive"
        :placeholder="
          $t(
            'umbrella-campaign.step-drama.drama-selection.select-motive-placeholder',
          )
        "
        :options="
          data.bperson_motives?.map(({ display_name, name, text }) => ({
            label: `${display_name} - ${text}`,
            value: name,
          })) ?? []
        "
        class="tw:grow"
      />

      <Icon icon="tabler-plus" class="tw:shrink-0 tw:text-2xl tw:md:mt-3" />

      <FieldSelect
        name="selected_barrier"
        :placeholder="
          $t(
            'umbrella-campaign.step-drama.drama-selection.select-barrier-placeholder',
          )
        "
        :options="
          data.bperson_barriers?.map(({ display_name, name, text }) => ({
            label: `${display_name} - ${text}`,
            value: name,
          })) ?? []
        "
        class="tw:grow"
      />
    </div>

    <div class="tw:w-fit">
      <ButtonRegenerate
        :regenerate="isInfoAvailable"
        :fetcher="handleClickGenerate"
      />
    </div>

    <template v-if="isInfoAvailable">
      <Separator />

      <CardBase class="tw:flex tw:flex-col tw:gap-5 tw:p-4">
        <CardTitle
          >{{
            $t(
              "umbrella-campaign.step-drama.drama-selection.emotional-tension-title",
            )
          }}
        </CardTitle>

        <FieldTextarea
          name="emotional_tension_title"
          :label="
            $t(
              'umbrella-campaign.step-drama.drama-selection.emotional-tension-label-title',
            )
          "
          :placeholder="
            $t(
              'umbrella-campaign.step-drama.drama-selection.emotional-tension-placeholder-title',
            )
          "
          required
        />

        <FieldTextarea
          name="emotional_tension_text"
          :label="
            $t(
              'umbrella-campaign.step-drama.drama-selection.emotional-tension-label-description',
            )
          "
          :placeholder="
            $t(
              'umbrella-campaign.step-drama.drama-selection.emotional-tension-placeholder-description',
            )
          "
          required
        />
      </CardBase>

      <CardBase class="tw:flex tw:flex-col tw:gap-5 tw:p-4">
        <CardTitle>{{
          $t("umbrella-campaign.step-drama.drama-selection.reasoning-title")
        }}</CardTitle>

        <FieldTextarea
          name="drama_reasoning"
          :placeholder="
            t(
              'umbrella-campaign.step-drama.drama-selection.reasoning-placeholder',
            )
          "
          required
        />
      </CardBase>

      <div class="tw:w-fit">
        <ButtonRegenerate
          :regenerate="areDramasAvailable"
          :fetcher="handleClickGenerateDramas"
        >
          <template #generate>
            {{
              $t(
                "umbrella-campaign.step-drama.drama-selection.button-generate-drama",
              )
            }}
          </template>

          <template #regenerate>
            {{
              $t(
                "umbrella-campaign.step-drama.drama-selection.button-regenerate-drama",
              )
            }}
          </template>
        </ButtonRegenerate>
      </div>
    </template>

    <template v-if="areDramasAvailable">
      <Separator />

      <CardTitle iconVariant="info" icon="tabler-device-tv">
        {{
          $t(
            "umbrella-campaign.step-drama.drama-selection.drama-proposal-title",
          )
        }}
      </CardTitle>

      <div class="tw:flex tw:justify-end">
        <ButtonGenerateIdea
          :fetcher="regenerateDramaList"
          useText
          color="primary"
          :textPlaceholder="
            $t(
              'umbrella-campaign.step-drama.drama-selection.ask-luca-modal.placeholder',
            )
          "
          :textMaxCharacters="250"
        >
          <template #title>
            {{
              $t(
                "umbrella-campaign.step-drama.drama-selection.ask-luca-modal.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "umbrella-campaign.step-drama.drama-selection.ask-luca-modal.description",
              )
            }}
          </template>

          <template #submit>
            {{
              $t(
                "umbrella-campaign.step-drama.drama-selection.ask-luca-modal.submit",
              )
            }}
          </template>

          {{ $t("global.ask-luca") }}
        </ButtonGenerateIdea>
      </div>

      <CardGrid>
        <CardBase
          v-for="(drama, index) in values.dramas"
          class="tw:flex tw:flex-col tw:gap-4 tw:p-6"
          :color="values.preferred_drama === drama.id ? 'primary' : 'default'"
        >
          <FieldEditableText
            :name="`dramas.${index}.title`"
            required
            class="tw:mb-1 tw:text-lg tw:leading-tight tw:font-extrabold"
            variant="text"
          />

          <FieldEditableText :name="`dramas.${index}.text`" required />

          <div class="tw:flex tw:flex-col tw:gap-2">
            <ButtonGenerateIdea
              :fetcher="regenerateSingleDrama(index)"
              useText
              color="primary"
              size="sm"
              variant="outlined"
              class="tw:bg-white"
              :textPlaceholder="
                $t(
                  'umbrella-campaign.step-drama.drama-selection.ask-luca-modal.placeholder',
                )
              "
              :textMaxCharacters="250"
            >
              <template #title>
                {{
                  $t(
                    "umbrella-campaign.step-drama.drama-selection.ask-luca-modal.title",
                  )
                }}
              </template>

              <template #description>
                {{
                  $t(
                    "umbrella-campaign.step-drama.drama-selection.ask-luca-modal.description",
                  )
                }}
              </template>

              <template #submit>
                {{
                  $t(
                    "umbrella-campaign.step-drama.drama-selection.ask-luca-modal.submit",
                  )
                }}
              </template>

              {{ $t("global.ask-luca") }}
            </ButtonGenerateIdea>

            <Button
              class="tw:w-full"
              type="button"
              @click="handleSelect(index)"
              size="sm"
              :isLoading="index === values.preferred_drama && isSubmitting"
              :disabled="index !== values.preferred_drama && isSubmitting"
            >
              {{
                $t(
                  "umbrella-campaign.step-drama.drama-selection.button-select-drama",
                )
              }}
            </Button>
          </div>
        </CardBase>
      </CardGrid>
    </template>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
