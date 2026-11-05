<script lang="ts">
import { useField } from "vee-validate";
import { object, string, InferType, boolean, number } from "yup";
import {
  ImageGeneration,
  imageGenerationSchema,
} from "@/components/images/image-generation/ImageGenerator.vue";
import ThirdPhaseCampaigns from "@/services/legacy/ThirdPhaseCampaigns";

export const campaignConceptSchema = object().shape({
  id: number().required(),
  selected: boolean(),
  title: string().required(),
  description: string().required(),
  concept: string().required(),
  message: string().required(),
  slogan: string().required(),
  imageGeneration: imageGenerationSchema,
});

export type CampaignConcept = InferType<typeof campaignConceptSchema>;
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
  checked: [checked: boolean];
}>();

const { value: model } = useField<CampaignConcept>(props.name, undefined);
const { value: isSelected } = useField<boolean>(
  `${props.name}.selected`,
  undefined,
);
const { name: imageGenerationFieldName, setValue: setImageGenerationField } =
  useField<ImageGeneration>(`${props.name}.imageGeneration`);

watch(isSelected, () => {
  emits("checked", isSelected.value);
});

const handleGeneratePrompts = async () => {
  // Set loading
  setImageGenerationField({
    isLoading: true,
  });

  // Generate prompts
  await ThirdPhaseCampaigns.setPreferred(props.projectId, model.value.id);
  await ThirdPhaseCampaigns.savePreferred(
    props.projectId,
    ThirdPhaseCampaigns.mapSchemaToData(model.value),
  );
  const promptsResponse = await ThirdPhaseCampaigns.generatePrompts(
    props.projectId,
  );

  // Save fetched prompts
  setImageGenerationField({
    prompts: flattenPrompts(promptsResponse.data.campaign_image_prompts),
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

    <button
      class="tw:flex tw:flex-col tw:gap-5 tw:text-left"
      type="button"
      @click="isOpen = true"
    >
      <template v-if="!isExpanded">
        <Separator />

        <div class="card-description">
          <CardParagraph variant="light">
            {{ model.concept }}
          </CardParagraph>
        </div>
      </template>

      <template v-if="isExpanded">
        <Separator />

        <LegacyCreativeConceptCardSections :name="name" />
      </template>
    </button>

    <ModalStandard v-model="isOpen">
      <template #header>
        <CardTitle is="h2"> {{ model.title }}</CardTitle>
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
        <LegacyCreativeConceptCardSections :name="name" editable />
      </template>

      <template #right>
        <ImageGenerator
          :name="imageGenerationFieldName"
          @generatePrompts="handleGeneratePrompts"
        >
          <template #title> Generate creative concept visualizations </template>
          <template #description>
            6 creative concept prompts will be generated using the Buyer Persona
            details you’ve provided. Please double-check the information for
            accuracy before continuing.
          </template>
        </ImageGenerator>
      </template>
    </ModalStandard>
  </SelectableCard>
</template>
