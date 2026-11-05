<script setup lang="ts">
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";
import UmbrellaCampaignsApi from "@/services/projects/UmbrellaCampaignsApi";
import {
  ImageGeneratorFormAttributesObject,
  ImageGeneratorFormInput,
  ImageGeneratorFormOutput,
} from "@/components/images/image-generation/ImageGeneratorForm.vue";

const emit = defineEmits<{
  goBack: [];
}>();

const brandId = useBrandId();
const projectId = useProjectId();

const { data, saveData, goNext } =
  useMultiStepFormContext<UmbrellaCampaignFormData>();

const attributes = [
  "core_idea",
  "primary_visual",
  "emotion",
  "place",
  "target_audience",
] as const;
type AttributeName = (typeof attributes)[number];

const initialValues: ImageGeneratorFormInput<AttributeName> = {
  attributes: {
    core_idea:
      data.value.image_attributes_saved?.core_idea ??
      data.value.image_attributes_generated?.core_idea,
    primary_visual:
      data.value.image_attributes_saved?.primary_visual ??
      data.value.image_attributes_generated?.primary_visual,
    emotion:
      data.value.image_attributes_saved?.emotion ??
      data.value.image_attributes_generated?.emotion,
    place:
      data.value.image_attributes_saved?.place ??
      data.value.image_attributes_generated?.place,
    target_audience:
      data.value.image_attributes_saved?.target_audience ??
      data.value.image_attributes_generated?.target_audience,
  },
  prompts: data.value.image_prompts,
  selectedPrompt: data.value.preferred_image_prompt,
  image: data.value.thumbnail_url,
};

async function handleRegenerateAttributes() {
  const response = await UmbrellaCampaignsApi.generateImageAttributes(
    brandId,
    projectId,
    data.value.id,
  );

  saveData(response.data);

  return {
    place: response.data.image_attributes_generated?.place,
    emotion: response.data.image_attributes_generated?.emotion,
    core_idea: response.data.image_attributes_generated?.core_idea,
    primary_visual: response.data.image_attributes_generated?.primary_visual,
    target_audience: response.data.image_attributes_generated?.target_audience,
  };
}

async function handleSaveAttributes(
  attributes: ImageGeneratorFormAttributesObject<AttributeName>,
) {
  // Save attributes
  const response = await UmbrellaCampaignsApi.saveImageAttributes(
    brandId,
    projectId,
    data.value.id,
    {
      image_attributes_generated: data.value.image_attributes_generated,
      image_attributes_saved: {
        place: attributes.place,
        emotion: attributes.emotion,
        core_idea: attributes.core_idea,
        primary_visual: attributes.primary_visual,
        target_audience: attributes.target_audience,
      },
    },
  );

  saveData(response.data);
}

async function handleGeneratePrompts(
  attributes: ImageGeneratorFormAttributesObject<AttributeName>,
): Promise<string[]> {
  await handleSaveAttributes(attributes);

  // Generate prompts
  const response = await UmbrellaCampaignsApi.generateImagePrompts(
    brandId,
    projectId,
    data.value.id,
  );

  return await flattenPrompts(response.data.image_prompts);
}

async function handleSelectImage(
  values: ImageGeneratorFormOutput<AttributeName>,
) {
  await handleSaveAttributes(values.attributes);

  // Save preferred image prompt
  const response = await UmbrellaCampaignsApi.savePreferredPrompt(
    brandId,
    projectId,
    data.value.id,
    {
      id: values.selectedPromptIndex,
      preferred: 1,
      prompt: values.selectedPrompt,
    },
  );
  saveData(response.data);

  // Save image
  if (values.generatedImage instanceof Blob) {
    const imageResponse = await UmbrellaCampaignsApi.uploadImage(
      brandId,
      projectId,
      data.value.id,
      values.generatedImage,
    );

    saveData({
      thumbnail_url: imageResponse.data.thumbnail_url,
    });
  }

  goNext();
}
</script>

<template>
  <FormStepLayout is="div">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=uB81rH44TZU"
    >
      {{ $t("umbrella-campaign.step-image.create-prompt.title") }}
      <template #description>
        {{ $t("umbrella-campaign.step-image.create-prompt.optional") }}
      </template>
    </PageTitle>

    <ImageGeneratorForm
      :attributes="attributes"
      :initialValues="initialValues"
      :regenerateAttributesFn="handleRegenerateAttributes"
      :generatePromptsFn="handleGeneratePrompts"
      :selectImageFn="handleSelectImage"
    >
      <template #subtitle>
        {{ $t("umbrella-campaign.step-image.create-prompt.subtitle") }}
      </template>
      <template #alert-message>
        {{ $t("umbrella-campaign.step-image.create-prompt.alert.message") }}
      </template>
      <template #alert-regenerate>
        {{ $t("umbrella-campaign.step-image.create-prompt.alert.regenerate") }}
      </template>
      <template #image-generator-title>
        {{
          $t("umbrella-campaign.step-image.create-prompt.imagegenerator.title")
        }}
      </template>
      <template #image-generator-description>
        {{
          $t(
            "umbrella-campaign.step-image.create-prompt.imagegenerator.description",
          )
        }}
      </template>
    </ImageGeneratorForm>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack type="button" @click="emit('goBack')" />
        <ButtonNext @click="goNext" type="button" variant="outlined">
          {{ $t("umbrella-campaign.step-image.create-prompt.skip") }}
        </ButtonNext>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
