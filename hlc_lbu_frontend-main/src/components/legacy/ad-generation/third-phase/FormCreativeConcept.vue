<script lang="ts" setup>
import { array, object } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import {
  CreativeConcept,
  creativeConceptSchema,
} from "./cards/LegacyCreativeConceptCard.vue";
import { UnidentifiedError } from "@/services/common-errors";
import ThirdPhaseCreativeConcept from "@/services/legacy/ThirdPhaseCreativeConcept";
import ThirdPhaseCampaigns from "@/services/legacy/ThirdPhaseCampaigns";

const store = useAdGenerationStore();
const projectId = store.projectId;

if (!store.data.creative_concepts) {
  throw new UnidentifiedError();
}

const initialConcepts = store.data.creative_concepts.map((data) =>
  ThirdPhaseCreativeConcept.mapDataToSchema(data),
);

const { handleSubmit, values, meta, setFieldValue } = useFormWithErrorScrolling(
  {
    initialValues: {
      creativeConcepts: initialConcepts,
    },
    validationSchema: toTypedSchema(
      object().shape({
        creativeConcepts: array()
          .of(creativeConceptSchema)
          .required()
          .test((items) => {
            return items.some((item) => item.selected);
          }),
      }),
    ),
    keepValuesOnUnmount: true,
  },
);

const handleChecked = (checked: boolean, value: CreativeConcept) => {
  const index = values.creativeConcepts?.findIndex(
    (item) => item.id === value.id,
  );

  if (checked) {
    // Uncheck all except this one
    values.creativeConcepts?.forEach((_, _index) => {
      if (index != _index) {
        setFieldValue(`creativeConcepts.${_index}.selected`, false);
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

  // Save data locally
  const creativeConcepts = values.creativeConcepts.map((creativeConcept) =>
    ThirdPhaseCreativeConcept.mapSchemaToData(creativeConcept),
  );
  store.data.creative_concepts = creativeConcepts;
  store.data.preferred_creative_concept = creativeConcepts.find(
    (concept) => concept.preferred === 1,
  );

  // Save all creative concepts. We sort the array to move the selected creative concept to the end
  const sortedCampaigns = [...creativeConcepts].sort((a, b) =>
    a.preferred > b.preferred ? 1 : -1,
  );
  for (const campaign of sortedCampaigns) {
    // Set as preferred first, because the save endpoint doesn't accept an id, it saves the
    // preferred creative concept
    await ThirdPhaseCreativeConcept.setPreferred(projectId, campaign.id);

    // Save the creative concept
    await ThirdPhaseCreativeConcept.savePreferred(projectId, campaign);
  }

  // Generate the campaigns
  const campaignsResponse = await ThirdPhaseCampaigns.generate(projectId);
  store.data.campaigns = campaignsResponse.data.campaigns;
  store.data.preferred_campaign = undefined;

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
        Select a creative concept you’d prefer to test
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Select 1 concept you’d like to test.
      </WizardCardParagraph>
    </div>

    <CardGrid>
      <LegacyCreativeConceptCard
        v-for="(item, index) in values.creativeConcepts"
        :name="`creativeConcepts[${index}]`"
        @checked="(checked) => handleChecked(checked, item)"
        v-model:expanded="areCardsExpanded"
        class="tw:grow tw:basis-0"
      />
    </CardGrid>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext :isLoading="isLoading" :disabled="!meta.valid" />
    </WizardCardActions>
  </form>
</template>
