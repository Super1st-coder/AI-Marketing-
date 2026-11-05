<script setup lang="ts">
import { TargetCustomerFormData } from "../TargetCustomerForm.vue";
import BuyerPersonasApi from "@/services/BuyerPersonasApi";
import { flattenPrompts } from "@/utils/type-declarations";
import {
  ImageGeneratorFormAttributesObject,
  ImageGeneratorFormInput,
  ImageGeneratorFormOutput,
} from "@/components/images/image-generation/ImageGeneratorForm.vue";

const emit = defineEmits<{
  goBack: [];
}>();

const { t } = useI18n();
const brandId = useBrandId();

const { data, saveData, goNext } =
  useMultiStepFormContext<TargetCustomerFormData>();

const attributes = [
  "physical_appearance",
  "background",
  "activity_or_action",
  "objects_or_props",
  "expression_and_emotion",
] as const;
type AttributeName = (typeof attributes)[number];

const initialValues: ImageGeneratorFormInput<AttributeName> = {
  attributes: {
    physical_appearance:
      data.value.image_attributes_saved?.physical_appearance ??
      data.value.image_attributes_generated?.physical_appearance,
    background:
      data.value.image_attributes_saved?.background ??
      data.value.image_attributes_generated?.background,
    activity_or_action:
      data.value.image_attributes_saved?.activity_or_action ??
      data.value.image_attributes_generated?.activity_or_action,
    objects_or_props:
      data.value.image_attributes_saved?.objects_or_props ??
      data.value.image_attributes_generated?.objects_or_props,
    expression_and_emotion:
      data.value.image_attributes_saved?.expression_and_emotion ??
      data.value.image_attributes_generated?.expression_and_emotion,
  },
  prompts: data.value.image_prompts,
  selectedPrompt: data.value.preferred_image_prompt,
  image: data.value.thumbnail_url,
};

async function handleRegenerateAttributes() {
  const response = await BuyerPersonasApi.generateImageAttributes(
    brandId,
    data.value.id,
    { trigger_prompts: true },
  );

  saveData(response.data);

  return {
    physical_appearance:
      response.data.image_attributes_generated?.physical_appearance,
    background: response.data.image_attributes_generated?.background,
    activity_or_action:
      response.data.image_attributes_generated?.activity_or_action,
    objects_or_props:
      response.data.image_attributes_generated?.objects_or_props,
    expression_and_emotion:
      response.data.image_attributes_generated?.expression_and_emotion,
  };
}

async function handleSaveAttributes(
  attributes: ImageGeneratorFormAttributesObject<AttributeName>,
) {
  const response = await BuyerPersonasApi.saveImageAttributes(
    brandId,
    data.value.id,
    {
      image_attributes_generated: data.value.image_attributes_generated,
      image_attributes_saved: {
        physical_appearance: attributes.physical_appearance,
        background: attributes.background,
        activity_or_action: attributes.activity_or_action,
        objects_or_props: attributes.objects_or_props,
        expression_and_emotion: attributes.expression_and_emotion,
      },
    },
  );

  saveData(response.data);
}

async function handleGeneratePrompts(
  attributes: ImageGeneratorFormAttributesObject<AttributeName>,
): Promise<string[]> {
  await handleSaveAttributes(attributes);

  const response = await BuyerPersonasApi.generateImagePrompts(
    brandId,
    data.value.id,
  );
  return flattenPrompts(response.data.image_prompts);
}

async function handleSelectImage(
  values: ImageGeneratorFormOutput<AttributeName>,
) {
  await handleSaveAttributes(values.attributes);

  // Save preferred image prompt
  const response = await BuyerPersonasApi.savePreferredPrompt(
    brandId,
    data.value.id,
    {
      id: values.selectedPromptIndex,
      description: values.selectedPrompt,
      preferred: 1,
    },
  );

  saveData({ ...response.data });

  // Save image
  if (values.generatedImage instanceof Blob) {
    const imageResponse = await BuyerPersonasApi.uploadImage(
      brandId,
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
  <FormStepLayout is="div" :disabled="data.locked">
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=Kqw5Y6v0SoM"
    >
      {{ t("buyer-person.image.legacy.create.title") }}

      <template #description>
        {{ t("buyer-person.image.legacy.create.description") }}
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
        {{ t("buyer-person.image.legacy.create.edit-attributes") }}
      </template>
      <template #alert-message>
        {{
          t("buyer-person.image.legacy.create.attributes-incomplete-message")
        }}
      </template>
      <template #alert-regenerate>
        {{
          t("buyer-person.image.legacy.create.attributes-incomplete-regenerate")
        }}
      </template>
      <template #image-generator-title>
        {{ t("buyer-person.image.legacy.create.image-generator.title") }}
      </template>
      <template #image-generator-description>
        {{ t("buyer-person.image.legacy.create.image-generator.description") }}
      </template>
    </ImageGeneratorForm>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack type="button" @click="emit('goBack')" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
