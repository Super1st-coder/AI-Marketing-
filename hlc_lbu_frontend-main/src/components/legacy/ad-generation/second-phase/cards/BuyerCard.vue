<script lang="ts">
import { useField } from "vee-validate";
import { array, object, string, InferType, boolean, number } from "yup";
import SecondPhaseBuyerPerson from "@/services/legacy/SecondPhaseBuyerPerson";
import { flattenPrompts } from "@/utils/type-declarations";
import {
  ImageGeneration,
  imageGenerationSchema,
} from "@/components/images/image-generation/ImageGenerator.vue";

export const targetBuyerSchema = object().shape({
  id: number().required(),
  selected: boolean(),
  title: string().required(),
  name: string().required(),
  age: number().required(),
  description: string().required(),
  lives: string().required(),
  values: string().required(),
  goals: array().of(string().required()).required(),
  needs: array().of(string().required()).required(),
  painPoints: array().of(string().required()).required(),
  imageGeneration: imageGenerationSchema,
});
//const storefirstPhase = useAdGenerationFirstPhaseStore();
export type TargetBuyer = InferType<typeof targetBuyerSchema>;
</script>

<script lang="ts" setup>
interface Props {
  name: string;
  projectId: number;
  selected?: boolean;
}

const props = defineProps<Props>();
const isOpen = ref(false);
const isExpanded = defineModel<boolean>("expanded");

const emits = defineEmits<{
  checked: [checked: boolean, value: TargetBuyer];
}>();

const { value: model } = useField<TargetBuyer>(props.name, undefined);
const { value: isSelected } = useField<boolean>(
  `${props.name}.selected`,
  undefined,
);

watch(isSelected, () => {
  emits("checked", isSelected.value, model.value);
});

const { name: imageGenerationFieldName, setValue: setImageGenerationField } =
  useField<ImageGeneration>(`${props.name}.imageGeneration`);

const handleGeneratePrompts = async () => {
  // Set loading
  setImageGenerationField({
    isLoading: true,
  });

  // Generate prompts
  await SecondPhaseBuyerPerson.setPreferred(props.projectId, model.value.id);
  await SecondPhaseBuyerPerson.savePreferred(
    props.projectId,
    SecondPhaseBuyerPerson.mapSchemaToData(model.value),
  );
  const promptsResponse = await SecondPhaseBuyerPerson.generatePrompts(
    props.projectId,
  );

  // Save prompts
  setImageGenerationField({
    prompts: flattenPrompts(promptsResponse.data.buyer_person_image_prompts),
  });
};
</script>

<template>
  <SelectableCard
    v-model:selected="isSelected"
    expandable
    v-model:expanded="isExpanded"
  >
    <template #header>
      <CardTitle is="h2">
        {{ model.title }}
      </CardTitle>
    </template>

    <ButtonAskLuca v-if="isExpanded" />

    <Separator />

    <button
      class="tw:flex tw:flex-col tw:gap-5 tw:text-left"
      type="button"
      @click="isOpen = true"
    >
      <div class="card-title-and-paragraph">
        <CardTitle>
          {{
            $t("process.target-buyer.card.name", {
              name: model.name,
              age: model.age,
            })
          }}
        </CardTitle>

        <CardParagraph variant="light">
          {{ model.description }}
        </CardParagraph>
      </div>

      <template v-if="isExpanded">
        <Separator />

        <BuyerCardSections :name="name" />
      </template>
    </button>

    <ModalStandard v-model="isOpen">
      <template #header>
        <CardTitle is="h2"> {{ model.title }} : {{ model.name }} </CardTitle>
        <CardParagraph variant="light">
          {{ model.description }}
        </CardParagraph>
      </template>

      <template #headerActions>
        <ButtonAskLuca class="tw:grow" />
        <ButtonCheck
          @click="isSelected = !isSelected"
          type="button"
          :checked="isSelected"
        />
      </template>

      <template #body>
        <BuyerCardSections :name="name" editable />
      </template>

      <template #right>
        <ImageGenerator
          :name="imageGenerationFieldName"
          @generatePrompts="handleGeneratePrompts"
        >
          <template #title>
            {{ $t("process.target-buyer.image-generator.title") }}
          </template>
          <template #description>
            {{ $t("process.target-buyer.image-generator.description") }}
          </template>
        </ImageGenerator>
      </template>
    </ModalStandard>
  </SelectableCard>
</template>
