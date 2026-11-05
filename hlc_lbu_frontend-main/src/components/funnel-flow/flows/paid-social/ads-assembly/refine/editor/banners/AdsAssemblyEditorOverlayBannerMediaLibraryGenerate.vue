<script setup lang="ts">
import {
  ImageGeneratorFormAttributesObject,
  ImageGeneratorFormInput,
  ImageGeneratorFormOutput,
} from "@/components/images/image-generation/ImageGeneratorForm.vue";
import { UnidentifiedError } from "@/services/common-errors";
import AdsApi from "@/services/funnel-flow/paid-social/AdsApi";
import { CampaingStyleData } from "@/services/projects/CampaignsApi";

const props = defineProps<{ index: number; bannerName: string }>();

const store = useFunnelPaidSocialAdsAssemblyStore();

const fieldImage = useField<ImageLibraryFile | string | Blob | undefined>(
  `images.${props.index}.image`,
  undefined,
  { keepValueOnUnmount: true },
);

const banner = computed(() =>
  store.currentVariant?.media.images_banner?.find(
    (banner) => banner.name === props.bannerName,
  )!,
);

const currentScreen = ref<"style" | "prompt">(
  banner.value.image_style_id &&
    banner.value.image_attributes_generated &&
    Object.keys(banner.value.image_attributes_generated).length > 0
    ? "prompt"
    : "style",
);

const handleSetStyle = async (selectedStyle: CampaingStyleData) => {
  if (
    !store.currentAd ||
    !store.currentChannel ||
    !store.currentVariant ||
    !store.currentVariant.media.elements
  ) {
    throw new UnidentifiedError();
  }

  // Set image style
  await AdsApi.setMediaImageStyle(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    banner.value.name,
    selectedStyle.id,
  );

  // Generate image attributes
  await AdsApi.generateMediaImageAttributes(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    banner.value.name,
    {
      elements: store.currentVariant.media.elements,
    },
  );

  // Refetch the ad
  await store.refetchCurrentAd();

  currentScreen.value = "prompt";
  await nextTick();
  await sleep(1000);
};

const attributes = [
  "core_idea",
  "primary_visual",
  "emotion",
  "place",
  "target_audience",
] as const;
type AttributeName = (typeof attributes)[number];

const initialValues = computed<ImageGeneratorFormInput<AttributeName>>(() => ({
  attributes: {
    core_idea:
      banner.value.image_attributes_saved?.core_idea ??
      banner.value.image_attributes_generated?.core_idea,
    primary_visual:
      banner.value.image_attributes_saved?.primary_visual ??
      banner.value.image_attributes_generated?.primary_visual,
    emotion:
      banner.value.image_attributes_saved?.emotion ??
      banner.value.image_attributes_generated?.emotion,
    place:
      banner.value.image_attributes_saved?.place ??
      banner.value.image_attributes_generated?.place,
    target_audience:
      banner.value.image_attributes_saved?.target_audience ??
      banner.value.image_attributes_generated?.target_audience,
  },
  prompts: banner.value.image_prompts,
  selectedPrompt: banner.value.preferred_image_prompt,
  image: fieldImage.value.value,
}));

async function handleRegenerateAttributes() {
  if (!store.currentAd || !store.currentChannel || !store.currentVariant) {
    throw new UnidentifiedError();
  }

  await AdsApi.generateMediaImageAttributes(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    banner.value.name,
    {
      elements: store.currentVariant.media.elements ?? [],
    },
  );

  // Refetch the ad
  await store.refetchCurrentAd();

  const generatedAttributes = banner.value.image_attributes_generated;
  return {
    place: generatedAttributes?.place,
    emotion: generatedAttributes?.emotion,
    core_idea: generatedAttributes?.core_idea,
    primary_visual: generatedAttributes?.primary_visual,
    target_audience: generatedAttributes?.target_audience,
  };
}

async function handleSaveAttributes(
  attributes: ImageGeneratorFormAttributesObject<AttributeName>,
) {
  if (
    !store.currentAd ||
    !store.currentChannel ||
    !store.currentVariant ||
    !banner.value.image_attributes_generated
  ) {
    throw new UnidentifiedError();
  }

  await AdsApi.saveMediaImageAttributes(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    banner.value.name,
    {
      image_attributes_generated: banner.value.image_attributes_generated,
      image_attributes_saved: {
        place: attributes.place,
        emotion: attributes.emotion,
        core_idea: attributes.core_idea,
        primary_visual: attributes.primary_visual,
        target_audience: attributes.target_audience,
      },
    },
  );

  // Refetch the ad
  await store.refetchCurrentAd();
}

async function handleGeneratePrompts(
  attributes: ImageGeneratorFormAttributesObject<AttributeName>,
): Promise<string[]> {
  if (
    !store.currentAd ||
    !store.currentChannel ||
    !store.currentVariant ||
    !store.currentVariant.media.elements
  ) {
    throw new UnidentifiedError();
  }

  await handleSaveAttributes(attributes);

  await AdsApi.generateMediaImagePrompts(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    banner.value.name,
    {
      elements: store.currentVariant.media.elements,
    },
  );

  // Refetch the ad
  await store.refetchCurrentAd();

  const imagePrompts = banner.value.image_prompts;
  return flattenPrompts(imagePrompts);
}

async function handleSelectImage(
  values: ImageGeneratorFormOutput<AttributeName>,
) {
  if (!store.currentAd || !store.currentChannel || !store.currentVariant) {
    throw new UnidentifiedError();
  }

  await handleSaveAttributes(values.attributes);

  // Save preferred image prompt
  await AdsApi.saveMediaImagePreferredPrompt(
    store.brandId,
    store.campaignId,
    store.currentAd.ad_id,
    store.currentChannel.channel_id,
    store.currentVariant.id,
    banner.value.name,
    {
      id: values.selectedPromptIndex,
      preferred: 1,
      description: values.selectedPrompt,
    },
  );

  // Refetch the ad
  await store.refetchCurrentAd();

  // Save image
  if (values.generatedImage instanceof Blob) {
    const imageLibraryStore = useImageLibraryStore();
    const file = new File([values.generatedImage], `${banner.value.name}`, {
      type: values.generatedImage.type,
    });

    imageLibraryStore.setSelectedFile(file, { cropped: true, source: "ia" });
  }
}
</script>

<template>
  <div class="tw:p-6">
    <!-- Style selection -->
    <div v-if="currentScreen === 'style'" class="tw:flex tw:flex-col tw:gap-6">
      <StyleSelectionGrid :setStyle="handleSetStyle">
        <template #title>
          {{
            $t(
              "funnel-flow.paid-social.ads.refine.editor.banner.choose-image-style",
            )
          }}
        </template>

        <template #description>
          {{
            $t(
              "funnel-flow.paid-social.ads.refine.editor.banner.choose-image-style-description",
            )
          }}
        </template>
      </StyleSelectionGrid>
    </div>
    <!-- Image generation -->
    <div v-else-if="currentScreen === 'prompt'">
      <!-- TODO: add help video URL later -->
      <PageTitle>
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
            $t(
              "campaigns.campaignsimage.image.createprompt.imagegenerator.title",
            )
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

      <ButtonGoBack type="button" @click="currentScreen = 'style'" />
    </div>
  </div>
</template>
