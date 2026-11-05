<script lang="ts" setup>
import { toTypedSchema } from "@vee-validate/yup";
import { object } from "yup";
import { categoryRefinerSchema } from "@/components/forms/category-refiner/categoryRefinerSchema";
import {
  getRefinerCategories,
  transformRefinerCategoriesToJson,
} from "@/components/forms/category-refiner/categoryRefinerTypes";
import FirstPhaseServices from "@/services/legacy/FirstPhaseServices";

const store = useAdGenerationStore();

const isLoading = ref(false);

const initialItems = getRefinerCategories(
  store.data.target_customer_attributes_saved,
  store.data.target_customer_attributes_generated,
  { canBeDeleted: true, minimumItems: 1 },
);

const { handleSubmit } = useFormWithErrorScrolling({
  initialValues: {
    yourTargetFeatures: initialItems,
  },
  validationSchema: toTypedSchema(
    object().shape({
      yourTargetFeatures: categoryRefinerSchema,
    }),
  ),
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Save data locally
  const savedAttributes = transformRefinerCategoriesToJson(
    values.yourTargetFeatures,
    true,
  );

  // Send data
  const response = await FirstPhaseServices.defineTargetConsumerAttributes(
    store.projectId,
    store.data.target_customer_attributes_generated!,
    savedAttributes,
  );

  // Save data from response
  store.data.target_customer_attributes_generated =
    response.data.target_customer_attributes_generated;
  store.data.target_customer_attributes_saved =
    response.data.target_customer_attributes_saved;

  // Go next
  store.goNext();
});
</script>

<template>
  <form @submit="onSubmit" class="tw:flex tw:flex-col tw:gap-[60px]">
    <div>
      <WizardCardTitle>
        {{ $t("process.your-target-refinement.title") }}
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph class="tw:mb-2.5 tw:whitespace-break-spaces">
        {{ $t("process.your-target-refinement.description") }}
      </WizardCardParagraph>

      <p class="tw:text-xl tw:font-extrabold">
        {{ store.data.brand_name }} |
        {{ store.data.product_name }}
      </p>
    </div>

    <CategoryRefinerField
      name="yourTargetFeatures"
      create
      :newCategoryDefaultProps="{ minimumItems: 1 }"
    />

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext :isLoading="isLoading" />
    </WizardCardActions>
  </form>
</template>
