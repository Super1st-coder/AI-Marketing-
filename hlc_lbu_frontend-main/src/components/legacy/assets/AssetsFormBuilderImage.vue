<script setup lang="ts">
import AssetsApi, { AssetTemplateElement } from "@/services/legacy/AssetsApi";
import { CampaingStyleData } from "@/services/projects/CampaignsApi";
import { AssetsFormData } from "./AssetsForm.vue";

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();

const { data, saveData } = useMultiStepFormContext<Required<AssetsFormData>>();
const currentImageData = computed(
  () => data.value.currentTemplate.images[data.value.currentImageIndex],
);

const imageField = useField<Blob | undefined>(
  () => `images[${data.value.currentImageIndex}].image`,
);

const tone = useFieldValue<string>("tone");
const extra_context = useFieldValue<string>("extra_context");
const elements = useFieldValue<AssetTemplateElement[]>("elements");
const language = useFieldValue<string | undefined>("language");

const currentScreen = ref<"createStyle" | "createPrompt">(
  currentImageData.value.image_style_id &&
    currentImageData.value.image_attributes_generated &&
    Object.keys(currentImageData.value.image_attributes_generated).length > 0
    ? "createPrompt"
    : "createStyle",
);

const handleSetStyle = async (selectedCampaign: CampaingStyleData) => {
  const { data: response1 } = await AssetsApi.setTemplateImageStyle(
    brandId,
    projectId,
    campaignId,
    data.value.currentTemplate.template_id,
    currentImageData.value.name,
    selectedCampaign.id,
  );

  const { data: response2 } = await AssetsApi.generateTemplateImageAttributes(
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

  saveData({
    currentTemplate: {
      ...data.value.currentTemplate,
      ...response1,
      ...response2,
    },
  });
};

const handleExit = () => {
  saveData({ currentImageIndex: undefined });
};

const handleGoBack = () => {
  handleExit();
};

const saveImage = (image: Blob) => {
  imageField.setValue(image);
  handleExit();
};
</script>

<template>
  <Suspense suspensible timeout="0">
    <StyleSelectionGrid
      :setStyle="handleSetStyle"
      v-if="currentScreen === 'createStyle'"
      @goBack="handleGoBack"
      @goNext="currentScreen = 'createPrompt'"
    />
    <AssetsFormBuilderImageCreatePrompt
      v-else-if="currentScreen === 'createPrompt'"
      @goBack="currentScreen = 'createStyle'"
      @skip="handleExit"
      @goNext="saveImage"
    />

    <template #fallback>
      <CircleLoaderDefault class="tw:min-h-[calc(100vh-66px)] tw:w-full" />
    </template>
  </Suspense>
</template>
