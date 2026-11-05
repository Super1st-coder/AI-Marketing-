<script lang="ts" setup>
import { object } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import {
  getRefinerCategories,
  transformRefinerCategoriesToJson,
} from "@/components/forms/category-refiner/categoryRefinerTypes";
import { categoryRefinerSchema } from "@/components/forms/category-refiner/categoryRefinerSchema";
import ThirdPhaseCreativeConcept from "@/services/legacy/ThirdPhaseCreativeConcept";

const store = useAdGenerationStore();
const projectId = store.projectId;

const initialItems = getRefinerCategories(
  store.data.creative_concept_attributes_saved,
  store.data.creative_concept_attributes_generated,
  { canBeDeleted: true, minimumItems: 1 },
);

const { handleSubmit } = useFormWithErrorScrolling({
  initialValues: {
    creativeDirectorRefinement: initialItems,
  },
  validationSchema: toTypedSchema(
    object().shape({ creativeDirectorRefinement: categoryRefinerSchema }),
  ),
  keepValuesOnUnmount: true,
});

const isLoading = ref(false);

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save attributes
  const savedAttributes = transformRefinerCategoriesToJson(
    values.creativeDirectorRefinement,
    true,
  );
  const saveResponse = await ThirdPhaseCreativeConcept.saveAttributes(
    projectId,
    store.data.creative_concept_attributes_generated!,
    savedAttributes,
  );

  // Save data from response
  store.data.creative_concept_attributes_generated =
    saveResponse.data.creative_concept_attributes_generated;
  store.data.creative_concept_attributes_saved =
    saveResponse.data.creative_concept_attributes_generated;

  // Generate the creative concepts
  const campaignsResponse = await ThirdPhaseCreativeConcept.generate(projectId);
  store.data.creative_concepts = campaignsResponse.data.creative_concepts;
  store.data.preferred_creative_concept = undefined;

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
        Creative concept refinement
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Based on your input, we’ve created creative concept guidelines. Please
        review and uncheck any items that don’t align with your vision.
      </WizardCardParagraph>
    </div>

    <CategoryRefinerField
      name="creativeDirectorRefinement"
      create
      :newCategoryDefaultProps="{ minimumItems: 1 }"
    />

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext :isLoading="isLoading" />
    </WizardCardActions>
  </form>
</template>
