<script lang="ts" setup>
import { object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import ThirdPhaseCreativeConcept from "@/services/legacy/ThirdPhaseCreativeConcept";

const store = useAdGenerationStore();
const projectId = store.projectId;

const { handleSubmit, meta } = useFormWithErrorScrolling({
  initialValues: {
    timeFrame: store.data.creative_concept_description?.time_frame,
    regions: store.data.creative_concept_description?.target_regions,
    consumerInsight: store.data.creative_concept_description?.consumer_insight,
    valueProposition:
      store.data.creative_concept_description?.value_proposition,
    communicationObjective:
      store.data.creative_concept_description?.communication_objetive,
    campaignPersonality:
      store.data.creative_concept_description?.tone_brand_personality,
    bigIdea: store.data.creative_concept_description?.big_idea,
  },
  validationSchema: toTypedSchema(
    object().shape({
      timeFrame: string().required(),
      regions: string().required(),
      consumerInsight: string().required(),
      valueProposition: string().required(),
      communicationObjective: string().required(),
      campaignPersonality: string().required(),
      bigIdea: string().required(),
    }),
  ),
  keepValuesOnUnmount: true,
});

const isLoading = ref(false);

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Send data
  const response = await ThirdPhaseCreativeConcept.saveDescription(projectId, {
    consumer_insight: values.consumerInsight,
    value_proposition: values.valueProposition,
    communication_objetive: values.communicationObjective,
    tone_brand_personality: values.campaignPersonality,
    big_idea: values.bigIdea,
    time_frame: values.timeFrame,
    target_regions: values.regions,
  });

  // Save data from response
  store.data.creative_concept_description =
    response.data.creative_concept_description;
  store.data.creative_concept_attributes_generated =
    response.data.creative_concept_attributes_generated;
  store.data.creative_concept_attributes_saved = undefined;

  // Go to next step
  store.goNext();
});
//#endregion
</script>

<template>
  <form
    @submit="onSubmit"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        Add more details to refine your creative concept
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Provide key details to optimize the generation process.
      </WizardCardParagraph>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-12">
      <FieldText
        name="timeFrame"
        label="What's the time frame for this campaign?"
        placeholder="Q4 2024 (October - December)"
        required
      />

      <FieldText
        name="regions"
        label="Which cities or regions will this campaign target?"
        placeholder="Mexico City, Guadalajara, Monterrey"
        required
      />

      <FieldText
        name="consumerInsight"
        label="Consumer insight"
        description="What key desires, frustrations, or needs have you identified in your audience? How does your product fit into their daily lives?"
        placeholder="e.g. Our audience values convenience and exclusivity but is frustrated with slow service and high fees from traditional providers."
        required
      />

      <FieldText
        name="valueProposition"
        label="Value proposition"
        description="What’s the key benefit of your product, and how does it stand out from the competition?"
        placeholder="e.g. Our product offers lower fees, exclusive perks for frequent buyers, and personalized advice, setting us apart from traditional competitors."
        required
      />

      <FieldText
        name="communicationObjective"
        label="Communication objective"
        description="What is the main goal of this campaign, and how does it support your overall brand strategy?"
        placeholder="e.g. We want to raise awareness and position our product as the top choice for individuals seeking exclusivity and convenience."
        required
      />

      <FieldText
        name="campaignPersonality"
        label="Tone and campaign personality"
        description="What tone and personality will resonate best with your audience in this campaign?"
        placeholder="e.g. Light-hearted, playful, and cheerful"
        required
      />

      <FieldText
        name="bigIdea"
        label="Big idea"
        description="What is the core message you want your audience to remember after engaging with the campaign?"
        placeholder="e.g. This product gives customers unique access to exclusive experiences and financial freedom."
        required
      />
    </div>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext :isLoading="isLoading" :disabled="!meta.valid" />
    </WizardCardActions>
  </form>
</template>
