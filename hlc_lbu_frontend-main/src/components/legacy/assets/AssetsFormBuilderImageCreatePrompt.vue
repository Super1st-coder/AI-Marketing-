<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import {
  imageGenerationSchema,
  ImageGeneratorFetcher,
} from "@/components/images/image-generation/ImageGenerator.vue";
import {
  ImageRequiredAttributesEmpty,
  UnidentifiedError,
} from "@/services/common-errors";
import ImageGenerationAPI from "@/services/ImageGenerationAPI";
import { useMutation } from "@tanstack/vue-query";
import { AssetsFormData } from "./AssetsForm.vue";
import AssetsApi, { AssetTemplateElement } from "@/services/legacy/AssetsApi";

const emit = defineEmits<{
  goBack: [];
  goNext: [image: Blob];
  skip: [];
}>();

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();

const tone = useFieldValue<string>("tone");
const extra_context = useFieldValue<string>("extra_context");
const elements = useFieldValue<AssetTemplateElement[]>("elements");
const language = useFieldValue<string | undefined>("language");

const { data, saveData } = useMultiStepFormContext<Required<AssetsFormData>>();
const currentImageData = computed(
  () => data.value.currentTemplate.images[data.value.currentImageIndex],
);

const initialImage = await AssetsApi.getTemplateImage(
  brandId,
  projectId,
  campaignId,
  data.value.currentTemplate.template_id,
  currentImageData.value.name,
);

const schema = computed(() =>
  toTypedSchema(
    object({
      place: string().required(t("forms.required-field")),
      emotion: string().required(t("forms.required-field")),
      core_idea: string().required(t("forms.required-field")),
      primary_visual: string().required(t("forms.required-field")),
      target_audience: string().required(t("forms.required-field")),
      imageGeneration: imageGenerationSchema,
    }),
  ),
);

const { handleSubmit, values, isSubmitting, resetForm, meta } =
  useFormWithErrorScrolling({
    validateOnMount: true,
    validationSchema: schema,
    initialValues: {
      place:
        currentImageData.value.image_attributes_saved?.place ??
        currentImageData.value.image_attributes_generated?.place,
      emotion:
        currentImageData.value.image_attributes_saved?.emotion ??
        currentImageData.value.image_attributes_generated?.emotion,
      core_idea:
        currentImageData.value.image_attributes_saved?.core_idea ??
        currentImageData.value.image_attributes_generated?.core_idea,
      primary_visual:
        currentImageData.value.image_attributes_saved?.primary_visual ??
        currentImageData.value.image_attributes_generated?.primary_visual,
      target_audience:
        currentImageData.value.image_attributes_saved?.target_audience ??
        currentImageData.value.image_attributes_generated?.target_audience,
      // Only display the prompts if the attributes have been saved
      imageGeneration: currentImageData.value.image_attributes_saved
        ? ImageGenerationAPI.mapDataToSchema(
            currentImageData.value.image_prompts,
            currentImageData.value.preferred_image_prompt,
            initialImage,
          )
        : undefined,
    },
  });

const handleGeneratePrompts: ImageGeneratorFetcher = async () => {
  if (
    !values.place ||
    !values.emotion ||
    !values.core_idea ||
    !values.primary_visual ||
    !values.target_audience
  ) {
    throw new ImageRequiredAttributesEmpty();
  }

  // Save attributes
  await AssetsApi.saveTemplateImageAttributes(
    brandId,
    projectId,
    campaignId,
    data.value.currentTemplate.template_id,
    currentImageData.value.name,
    {
      image_attributes_generated:
        currentImageData.value.image_attributes_generated,
      image_attributes_saved: {
        place: values.place,
        emotion: values.emotion,
        core_idea: values.core_idea,
        primary_visual: values.primary_visual,
        target_audience: values.target_audience,
      },
    },
  );

  // Generate prompts
  const response = await AssetsApi.generateTemplateImagePrompts(
    brandId,
    projectId,
    campaignId,
    data.value.currentTemplate.template_id,
    currentImageData.value.name,
    {
      tone: tone.value,
      extra_context: extra_context.value,
      elements: elements.value,
      language: language.value,
    },
  );
  const newImageData = response.data.images.find(
    (image) => image.name === currentImageData.value.name,
  );
  if (!newImageData) {
    throw new UnidentifiedError();
  }

  saveData({
    currentTemplate: { ...data.value.currentTemplate, ...response.data },
  });

  return flattenPrompts(newImageData.image_prompts);
};

const onSubmit = handleSubmit(async (values) => {
  if (
    !values.imageGeneration ||
    !values.imageGeneration.generatedImage ||
    !values.imageGeneration.selectedPrompt ||
    values.imageGeneration.selectedPromptIndex === undefined
  ) {
    throw new UnidentifiedError();
  }

  // Save preferred image prompt
  const response = await AssetsApi.saveTemplateImagePreferredPrompt(
    brandId,
    projectId,
    campaignId,
    data.value.currentTemplate.template_id,
    currentImageData.value.name,
    {
      id: values.imageGeneration.selectedPromptIndex,
      preferred: 1,
      description: values.imageGeneration.selectedPrompt,
    },
  );
  saveData({
    currentTemplate: { ...data.value.currentTemplate, ...response.data },
  });

  // Save image
  if (values.imageGeneration.generatedImage instanceof Blob) {
    await AssetsApi.uploadTemplateImage(
      brandId,
      projectId,
      campaignId,
      data.value.currentTemplate.template_id,
      currentImageData.value.name,
      values.imageGeneration.generatedImage,
    );

    emit("goNext", values.imageGeneration.generatedImage);
  }
});

const displayBadGenerationWarning = computed(() => {
  return (
    // If some generated attributes are missing
    (!currentImageData.value.image_attributes_generated?.core_idea ||
      !currentImageData.value.image_attributes_generated?.emotion ||
      !currentImageData.value.image_attributes_generated?.place ||
      !currentImageData.value.image_attributes_generated?.primary_visual ||
      !currentImageData.value.image_attributes_generated?.target_audience) &&
    // and if the user has not filled in all the required fields
    !(
      values?.core_idea &&
      values?.emotion &&
      values?.place &&
      values?.primary_visual &&
      values?.target_audience
    )
  );
});

const regenerateMutation = useMutation({
  mutationFn: () => {
    return AssetsApi.generateTemplateImageAttributes(
      brandId,
      projectId,
      campaignId,
      data.value.currentTemplate.template_id,
      currentImageData.value.name,
      {
        tone: tone.value,
        extra_context: extra_context.value,
        elements: elements.value,
      },
    );
  },
  onSuccess: (response) => {
    saveData({
      currentTemplate: { ...data.value.currentTemplate, ...response.data },
    });

    const newImageData = response.data.images.find(
      (image) => image.name === currentImageData.value.name,
    );
    if (!newImageData) {
      throw new UnidentifiedError();
    }
    resetForm({
      values: {
        place: newImageData.image_attributes_generated?.place,
        emotion: newImageData.image_attributes_generated?.emotion,
        core_idea: newImageData.image_attributes_generated?.core_idea,
        primary_visual: newImageData.image_attributes_generated?.primary_visual,
        target_audience:
          newImageData.image_attributes_generated?.target_audience,
      },
    });
  },
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit">
    <PageTitle helpButton>
      {{ $t("campaigns.campaignsimage.image.createprompt.title") }}
      <template #description>
        {{ $t("campaigns.campaignsimage.image.createprompt.description") }}
      </template>
    </PageTitle>

    <div class="tw:flex tw:flex-col tw:gap-[30px] tw:lg:flex-row tw:lg:gap-10">
      <div class="tw:flex tw:basis-1/2 tw:flex-col tw:gap-12">
        <h2 class="tw:text-2xl tw:font-extrabold">
          {{ $t("campaigns.campaignsimage.image.createprompt.h2text") }}
        </h2>

        <Alert v-if="displayBadGenerationWarning" type="error">
          {{ $t("campaigns.campaignsimage.image.createprompt.alertmessage") }}
          <template #actions>
            <Button
              size="md"
              @click="regenerateMutation.mutate"
              :isLoading="regenerateMutation.isPending.value"
            >
              {{ $t("global.regenerate") }}
            </Button>
          </template>
        </Alert>

        <CardSections>
          <EditableCardSection
            name="core_idea"
            :title="
              $t('campaigns.campaignsimage.image.createprompt.coreideatitle')
            "
            icon="tabler-bulb"
            iconVariant="primary"
            editable
            required
          />

          <EditableCardSection
            name="primary_visual"
            :title="
              $t(
                'campaigns.campaignsimage.image.createprompt.primaryvisualtitle',
              )
            "
            icon="tabler-eye"
            iconVariant="info"
            editable
            required
          />

          <EditableCardSection
            name="emotion"
            :title="
              $t('campaigns.campaignsimage.image.createprompt.emotiontitle')
            "
            icon="tabler-mood-happy"
            iconVariant="error"
            editable
            required
          />

          <EditableCardSection
            name="place"
            :title="
              $t('campaigns.campaignsimage.image.createprompt.placetitle')
            "
            icon="tabler-map"
            iconVariant="success"
            editable
            required
          />

          <EditableCardSection
            name="target_audience"
            :title="
              $t(
                'campaigns.campaignsimage.image.createprompt.targetaudiencetitle',
              )
            "
            icon="ic:round-people-alt"
            iconVariant="primary"
            editable
            required
          />
        </CardSections>
      </div>

      <div>
        <Separator type="vertical" class="tw:hidden tw:lg:block" />
        <Separator type="horizontal" class="tw:lg:hidden" />
      </div>

      <ImageGenerator
        name="imageGeneration"
        class="tw:basis-1/2 tw:self-start tw:py-16"
        :promptFetcher="handleGeneratePrompts"
        useSubmitButton
        :submitButtonProps="{ isLoading: isSubmitting }"
        editablePrompts
      >
        <template #title>
          {{
            $t(
              "campaigns.campaignsimage.image.createprompt.imagegenerator.title",
            )
          }}
        </template>
        <template #description>
          {{
            $t(
              "campaigns.campaignsimage.image.createprompt.imagegenerator.description",
            )
          }}
        </template>
      </ImageGenerator>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack type="button" @click="emit('goBack')" />
        <ButtonNext @click="emit('skip')" type="button" variant="outlined">
          {{ $t("global.skip") }}
        </ButtonNext>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
