<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { InferType, mixed, object } from "yup";
import { ProductFormData } from "./ProductForm.vue";
import {
  getRefinerCategories,
  transformRefinerCategoriesToJson,
} from "../forms/category-refiner/categoryRefinerTypes";
import {
  mandatoryCategoryRefinerSchema,
  optionalCategoryRefinerSchema,
} from "../forms/category-refiner/categoryRefinerSchema";
import ProductsApi from "@/services/ProductsApi";
import { AskLucaFetcher } from "../forms/category-refiner/ModalAskLucaRefiner.vue";
import { CategoryRefinerFieldAskLuca } from "../forms/category-refiner/CategoryRefinerField.vue";

const { t } = useI18n();
const brandId = useBrandId();

const { data, saveData, goNext, goBack, getIsStageDirty, setDirtyStage } =
  useMultiStepFormContext<ProductFormData>();

// Build initial lists
let initialMandatoryItems = getRefinerCategories(
  data.value.mandatory_attributes_saved,
  data.value.mandatory_attributes_generated,
  { minimumItems: 3 },
);
let initialOptionalItems = getRefinerCategories(
  data.value.optional_attributes_saved,
  data.value.optional_attributes_generated,
);

// If coming from Summary with a requested category to edit, open that card
const focusCategory = (data.value as ProductFormData).refinerOpenCategory;
if (focusCategory) {
  const openByName = (list: typeof initialMandatoryItems) =>
    list.map((c) => (c.name === focusCategory ? { ...c, isOpen: true } : c));
  initialMandatoryItems = openByName(initialMandatoryItems);
  initialOptionalItems = openByName(initialOptionalItems);
}

// Schema when is unlocked
const unlockedSchema = object({
  locked: mixed<false>().oneOf([false]).required(),
  mandatory: mandatoryCategoryRefinerSchema,
  optional: optionalCategoryRefinerSchema,
});

// Schema when is locked
const lockedSchema = object({
  locked: mixed<true>().oneOf([true]).required(),
});

// Combine the schemas into a single schema
const schema = mixed<
  InferType<typeof unlockedSchema> | InferType<typeof lockedSchema>
>()
  .test("shape", "invalid", async (data) => {
    // Don't validate if it's locked
    if (data?.locked) return true;

    await unlockedSchema.validate(data);
    return true;
  })
  .required();

const { handleSubmit, meta, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: toTypedSchema(schema),
  initialValues: {
    locked: data.value.locked,
    mandatory: initialMandatoryItems,
    optional: initialOptionalItems,
  },
});

// Clear the focus flag so it only opens once
if (focusCategory) {
  saveData({ refinerOpenCategory: undefined } as Partial<ProductFormData>);
}

const { confirm } = useConfirmModal();

const onSubmit = handleSubmit(async (values) => {
  // Skip if it's locked
  if (values.locked) {
    goNext({ isDirty: false });
    return;
  }

  let triggerGeneration = true;

  // Display and wait for the confirm modal if needed
  if (data.value.product_story) {
    if (meta.value.dirty || getIsStageDirty("summary")) {
      // Display the modal if the data is dirty
      const result = await confirm();
      if (result === "close") {
        return;
      }

      triggerGeneration = result === "continue";
    } else {
      // If the data is not dirty, do not trigger prompts
      triggerGeneration = false;
    }
  }

  // Save attributes
  const response = await ProductsApi.saveAttributes(brandId, data.value.id, {
    mandatory_attributes_generated: data.value.mandatory_attributes_generated,
    mandatory_attributes_saved: transformRefinerCategoriesToJson(
      values.mandatory,
      true,
    ),
    optional_attributes_generated: data.value.optional_attributes_generated,
    optional_attributes_saved: transformRefinerCategoriesToJson(
      values.optional,
      true,
    ),
    not_advance: false,
    trigger_prompts: triggerGeneration,
  });

  // Save data and go next
  setDirtyStage("summary", false);
  saveData({ ...response.data });
  goNext({ isDirty: meta.value.dirty });
});

const askLucaFetcher: AskLucaFetcher = async (name, description, question) => {
  return (
    await ProductsApi.generateAttributesByCategory(brandId, data.value.id, {
      category: name,
      ask: question,
      answer: description,
    })
  ).data.attributes_generated;
};

const askLuca = computed<CategoryRefinerFieldAskLuca>(() => ({
  benefits: {
    fetcher: askLucaFetcher,
  },
  value_proposition: {
    fetcher: askLucaFetcher,
  },
  features: {
    fetcher: askLucaFetcher,
  },
  keywords: {
    fetcher: askLucaFetcher,
  },
  pricing: {
    fetcher: askLucaFetcher,
  },
  promotions: {
    fetcher: askLucaFetcher,
  },
  warranties: {
    fetcher: askLucaFetcher,
  },
  faqs: {
    fetcher: askLucaFetcher,
  },
  competitive_advantage: {
    fetcher: askLucaFetcher,
  },
}));
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=lyL2mVYzj1g"
    >
      {{ t("products.refine.title") }}

      <template #description>
        {{ t("products.refine.description") }}
      </template>
    </PageTitle>

    <CategoryRefinerField
      name="mandatory"
      :askLuca="askLuca"
      :disabled="data?.locked || isSubmitting"
    >
      <template #title>{{ t("refiner.mandatory-categories") }}</template>
    </CategoryRefinerField>

    <CategoryRefinerField
      name="optional"
      :askLuca="askLuca"
      create
      :disabled="data?.locked || isSubmitting"
    >
      <template #title>{{ t("refiner.optional-categories") }}</template>
    </CategoryRefinerField>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalConfirmRegeneration />
    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
