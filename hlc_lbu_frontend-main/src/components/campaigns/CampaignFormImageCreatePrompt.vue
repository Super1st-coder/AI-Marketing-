<script setup lang="ts">
import CampaignsApi from "@/services/projects/CampaignsApi";
import { flattenPrompts } from "@/utils/type-declarations";
import { CampaignFormData } from "./CampaignForm.vue";
import {
  ImageGeneratorFormAttributesObject,
  ImageGeneratorFormInput,
  ImageGeneratorFormOutput,
} from "@/components/images/image-generation/ImageGeneratorForm.vue";
import { useMultiStepFormContext } from "@/composables/multi-step-form/useMultiStepContext";

const emit = defineEmits<{
  goBack: [];
}>();

const brandId = useBrandId();
const projectId = useProjectId();

const { data, saveData, goNext } = useMultiStepFormContext<CampaignFormData>();

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
  const response = await CampaignsApi.GenerateCampaignImageAttributes(
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
  const response = await CampaignsApi.saveImageAttributes(
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

  const response = await CampaignsApi.generateImagePrompts(
    brandId,
    projectId,
    data.value.id,
  );

  return flattenPrompts(response.data.image_prompts);
}

async function handleSelectImage(
  values: ImageGeneratorFormOutput<AttributeName>,
) {
  await handleSaveAttributes(values.attributes);

  // Save preferred image prompt
  const response = await CampaignsApi.savePreferredPrompt(
    brandId,
    projectId,
    data.value.id,
    {
      id: values.selectedPromptIndex,
      preferred: 1,
      description: values.selectedPrompt,
    },
  );
  saveData(response.data);

  // Save image
  if (values.generatedImage instanceof Blob) {
    const imageResponse = await CampaignsApi.uploadImage(
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
      helpVideoUrl="https://www.youtube.com/watch?v=rZD4x4M9540"
    >
      {{ $t("campaigns.campaignsimage.image.createprompt.title") }}
      <template #description>
        {{ $t("campaigns.campaignsimage.image.createprompt.description") }}
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
        {{ $t("campaigns.campaignsimage.image.createprompt.h2text") }}
      </template>
      <template #alert-message>
        {{ $t("campaigns.campaignsimage.image.createprompt.alertmessage") }}
      </template>
      <template #alert-regenerate>
        {{ $t("global.regenerate") }}
      </template>
      <template #image-generator-title>
        {{
          $t("campaigns.campaignsimage.image.createprompt.imagegenerator.title")
        }}
      </template>
      <template #image-generator-description>
        {{
          $t(
            "campaigns.campaignsimage.image.createprompt.imagegenerator.description",
          )
        }}
      </template>
    </ImageGeneratorForm>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack type="button" @click="emit('goBack')" />
        <ButtonNext @click="goNext" type="button" variant="outlined">
          {{ $t("global.skip") }}
        </ButtonNext>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
