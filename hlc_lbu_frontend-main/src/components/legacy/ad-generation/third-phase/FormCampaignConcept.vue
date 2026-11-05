<script lang="ts" setup>
import { array, object } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import {
  CampaignConcept,
  campaignConceptSchema,
} from "./cards/CampaignConceptCard.vue";
import ThirdPhaseCampaigns from "@/services/legacy/ThirdPhaseCampaigns";
import { UnidentifiedError } from "@/services/common-errors";

const store = useAdGenerationStore();
const projectId = store.projectId;

if (!store.data.campaigns) {
  throw new UnidentifiedError();
}

const initialCampaigns = store.data.campaigns.map((data) =>
  ThirdPhaseCampaigns.mapDataToSchema(data),
);

// Map the prompts and fetch the image
const initialSelectedCampaign = initialCampaigns.find(
  (campaign) => campaign.selected,
);
if (initialSelectedCampaign) {
  const selectedPrompt = store.data.campaign_image_prompts?.find(
    (prompt) => prompt.preferred,
  );
  const imageBlob = await ThirdPhaseCampaigns.getImage(store.projectId, true);

  initialSelectedCampaign.imageGeneration = {
    prompts: store.data.buyer_person_image_prompts?.map(
      (prompt) => prompt.description,
    ),
    selectedPromptIndex: selectedPrompt?.id,
    selectedPrompt: selectedPrompt?.description,
    generatedImage: imageBlob,
  };
}

const { handleSubmit, values, setFieldValue, errors, submitCount } =
  useFormWithErrorScrolling({
    initialValues: {
      campaignConcepts: initialCampaigns,
    },
    validationSchema: toTypedSchema(
      object().shape({
        campaignConcepts: array()
          .of(campaignConceptSchema)
          .required()
          .test((items) => {
            return items.some((item) => item.selected);
          })
          .test(
            "need-image",
            "You have to generate an image in the selected concept.",
            (items) => {
              const selected = items.find((item) => item.selected);
              return !!selected?.imageGeneration?.generatedImage;
            },
          ),
      }),
    ),
    keepValuesOnUnmount: true,
  });

const selectedCampaignConcept = computed(() =>
  values.campaignConcepts?.find((item) => item.selected),
);

const handleChecked = (checked: boolean, value: CampaignConcept) => {
  const index = values.campaignConcepts?.findIndex(
    (item) => item.id === value.id,
  );

  if (checked) {
    // Uncheck all except this one
    values.campaignConcepts?.forEach((_, _index) => {
      if (index != _index) {
        setFieldValue(`campaignConcepts.${_index}.selected`, false);
      }
    });
  }
};

const areCardsExpanded = ref(false);

// Keep the height of cards
useMaxHeightCards(
  [
    ".card-header",
    ".card-description",
    ".card-concept",
    ".card-message",
    ".card-slogan",
  ],
  [values, areCardsExpanded],
);

//#region Submit

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  if (
    !selectedCampaignConcept.value ||
    !selectedCampaignConcept.value.imageGeneration?.generatedImage ||
    selectedCampaignConcept.value.imageGeneration?.selectedPromptIndex ===
      undefined
  ) {
    throw new UnidentifiedError();
  }

  // Save data locally
  const campaigns = values.campaignConcepts.map((creativeConcept) =>
    ThirdPhaseCampaigns.mapSchemaToData(creativeConcept),
  );
  store.data.campaigns = campaigns;
  store.data.preferred_campaign = campaigns.find(
    (campaign) => campaign.preferred === 1,
  );

  // Save all campaigns. We sort the array to move the selected campaign to the end
  const sortedCampaigns = [...campaigns].sort((a, b) =>
    a.preferred > b.preferred ? 1 : -1,
  );
  for (const campaign of sortedCampaigns) {
    // Set as preferred first, because the save endpoint doesn't accept an id, it saves the
    // preferred campaign
    await ThirdPhaseCampaigns.setPreferred(projectId, campaign.id);

    // Save the campaign
    await ThirdPhaseCampaigns.savePreferred(projectId, campaign);
  }

  // Set the preferred prompt
  const preferredPromptResponse = await ThirdPhaseCampaigns.setPreferredPrompt(
    store.projectId,
    selectedCampaignConcept.value.imageGeneration.selectedPromptIndex,
  );
  // Save data from response
  store.data.selected_campaign_image_prompt =
    preferredPromptResponse.data.selected_campaign_image_prompt;

  // Upload the image
  if (
    selectedCampaignConcept.value.imageGeneration.generatedImage instanceof Blob
  ) {
    await ThirdPhaseCampaigns.uploadImage(
      store.projectId,
      selectedCampaignConcept.value.imageGeneration.generatedImage,
    );
  }

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
      <CardTitle
        iconVariant="error"
        iconSrc="/images/magic-ball.png"
        class="tw:mb-8"
      >
        Your selected Creative Concept

        <template #subtitle>
          {{ store.data.preferred_creative_concept?.creative_concept.title }}
        </template>
      </CardTitle>

      <Separator />
    </div>

    <div>
      <WizardCardTitle>
        Choose the creative campaign you’d like to test
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Select one campaign to move forward with testing.
      </WizardCardParagraph>
    </div>

    <CardGrid>
      <CampaignConceptCard
        v-for="(item, index) in values.campaignConcepts"
        :name="`campaignConcepts[${index}]`"
        :projectId="projectId"
        @checked="(checked) => handleChecked(checked, item)"
        v-model:expanded="areCardsExpanded"
        class="tw:grow tw:basis-0"
      />
    </CardGrid>

    <Alert v-if="errors.campaignConcepts && submitCount > 0" type="error">
      {{ errors.campaignConcepts }}
    </Alert>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext
        :isLoading="isLoading"
        :disabled="!selectedCampaignConcept"
      />
    </WizardCardActions>
  </form>
</template>
