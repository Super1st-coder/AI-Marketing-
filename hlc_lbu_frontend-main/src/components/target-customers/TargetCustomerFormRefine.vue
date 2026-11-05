<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { InferType, mixed, object, array, string, number } from "yup"; // Agregamos 'array', 'string', 'number'
import {
  getRefinerCategories,
  transformRefinerCategoriesToJson,
} from "../forms/category-refiner/categoryRefinerTypes";
import { mandatoryCategoryRefinerSchema } from "../forms/category-refiner/categoryRefinerSchema";
import BuyerPersonasApi from "@/services/BuyerPersonasApi";
import { AskLucaFetcher } from "../forms/category-refiner/ModalAskLucaRefiner.vue";
import CategoryRefinerFieldGrouped, {
  CategoryRefinerFieldAskLuca,
  MandatoryAttributeGroup,
} from "../forms/category-refiner/CategoryRefinerFieldGrouped.vue";
import { TargetCustomerFormData } from "./TargetCustomerForm.vue";
import { LlmOutputError } from "@/services/common-errors";

const { t } = useI18n();
const brandId = useBrandId();

const { data, saveData, goBack, goNext, setDirtyStage, getIsStageDirty } =
  useMultiStepFormContext<TargetCustomerFormData>();

const initialMandatoryItems = getRefinerCategories(
  data.value.mandatory_attributes_saved,
  data.value.mandatory_attributes_generated,
  {
    minimumItems: 3,
    categories: {
      age_range: { minimumItems: 1 },
      hometown: { minimumItems: 1 },
      income_level_brackets: { minimumItems: 1 },
      occupation: { minimumItems: 1 },
      name_and_nickname: { minimumItems: 1, maxItems: 1 },
    },
  },
);

const attributeItemSchema = object({
  id: string().required(),
  idx: number().required(),
});

const mandatoryAttributeGroupSchema = object({
  id: string().required(),
  idx: number().required(),
  items: array(attributeItemSchema).required(),
  display_name: string().required(),
});

// Schema when is unlocked
const unlockedSchema = object({
  locked: mixed<false>().oneOf([false]).required(),
  attributes: object({
    mandatory: mandatoryCategoryRefinerSchema,
    mandatory_attributes_groups: array(
      mandatoryAttributeGroupSchema,
    ).required(),
  }),
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
    attributes: {
      mandatory: initialMandatoryItems,
      // Aseguramos que los valores iniciales incluyan los grupos y que estén ordenados por 'idx'
      mandatory_attributes_groups: [
        ...data.value.mandatory_attributes_groups,
      ].sort((a, b) => a.idx - b.idx),
    },
  },
});
const { confirm } = useConfirmModal();

const generalErrorMessage = ref<string>();

const mandatoryGroups = useFieldValue<MandatoryAttributeGroup[]>(
  "attributes.mandatory_attributes_groups",
);

const onSubmit = handleSubmit(async (values) => {
  try {
    generalErrorMessage.value = undefined;

    // Skip if it's locked
    if (values.locked) {
      goNext({ isDirty: false });
      return;
    }

    let triggerGeneration = true;

    // Display and wait for the confirm modal if needed
    if (data.value.bperson_story) {
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
    const response = await BuyerPersonasApi.saveAttributes(
      brandId,
      data.value.id,
      {
        mandatory_attributes_generated:
          data.value.mandatory_attributes_generated,
        mandatory_attributes_saved: transformRefinerCategoriesToJson(
          values.attributes.mandatory,
          true,
        ),
        trigger_prompts: triggerGeneration,
      },
    );

    // Save data and go next
    setDirtyStage("summary", false);
    if (meta.value.dirty) {
      setDirtyStage("image", true);
    }
    saveData({ ...response.data });
    goNext({ isDirty: meta.value.dirty });
  } catch (error) {
    if (error instanceof LlmOutputError) {
      generalErrorMessage.value = t(`errors.${error.message}.title`);
    } else {
      throw error;
    }
  }
});

const askLucaFetcher: AskLucaFetcher = async (name, description) => {
  return (
    await BuyerPersonasApi.generateAttributesByCategory(
      brandId,
      data.value.id,
      {
        category: name,
        ask: description,
        answer: description,
        description: description,
      },
    )
  ).data.attributes_generated;
};

const askLuca = computed<CategoryRefinerFieldAskLuca>(() => ({
  hometown: {
    fetcher: askLucaFetcher,
  },
  pain_points: {
    fetcher: askLucaFetcher,
  },
  customer_goal: {
    fetcher: askLucaFetcher,
  },
  fears_and_worries: {
    fetcher: askLucaFetcher,
  },
  problem_with_current_solution: {
    fetcher: askLucaFetcher,
  },
  how_they_solve_it_now: {
    fetcher: askLucaFetcher,
  },
  barriers_to_making_a_change: {
    fetcher: askLucaFetcher,
  },
  name_and_nickname: {
    fetcher: askLucaFetcher,
  },
  age_range: {
    fetcher: askLucaFetcher,
  },
  income_level_brackets: {
    fetcher: askLucaFetcher,
  },
}));
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=Q-UJOcSeWNU"
    >
      {{ t("buyer-person.refine.title") }}

      <template #description>
        {{ t("buyer-person.refine.description") }}
      </template>
    </PageTitle>

    <CategoryRefinerFieldGrouped
      name="attributes.mandatory"
      :groups="mandatoryGroups || []"
      :askLuca="askLuca"
      :disabled="data.locked || isSubmitting"
    />

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

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
