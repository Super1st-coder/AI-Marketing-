<script lang="ts" setup>
import { ImageGeneration } from "@/components/images/image-generation/ImageGenerator.vue";
import { LandingPage } from "@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/landing-page/landing-page.vue";
import { useField, useFormValues } from "vee-validate";

const { value: values } = useFormValues<LandingPage>();

useMaxHeightCards(
  [
    ".hero-title",
    ".hero-image",
    ".hero-subtitle",
    ".hero-paragraph",
    ".hero-cta",
  ],
  [values],
);

const { name: imageGenerationFieldName, setValue: setImageGenerationField } =
  useField<ImageGeneration>("heroImage");

const handleGeneratePrompts = async () => {
  // Set loading
  setImageGenerationField({
    isLoading: true,
  });

  await sleep(1000);

  const prompts = [
    "Photo of a 30-year-old professional photographer, intense focus evident in his gaze, capturing a perfect shot in the vibrant streets of Berlin. He holds a sleek camera with innovative features, highlighting his commitment to high-quality imaging and creativity.",
    "Photo of a 30-year-old professional photographer, intense focus evident in his gaze, capturing a perfect shot in the vibrant streets of Berlin. He holds a sleek camera with innovative features, highlighting his commitment to high-quality imaging and creativity.",
    "Photo of a 30-year-old professional photographer, intense focus evident in his gaze, capturing a perfect shot in the vibrant streets of Berlin. He holds a sleek camera with innovative features, highlighting his commitment to high-quality imaging and creativity.",
    "Photo of a 30-year-old professional photographer, intense focus evident in his gaze, capturing a perfect shot in the vibrant streets of Berlin. He holds a sleek camera with innovative features, highlighting his commitment to high-quality imaging and creativity.",
    "Photo of a 30-year-old professional photographer, intense focus evident in his gaze, capturing a perfect shot in the vibrant streets of Berlin. He holds a sleek camera with innovative features, highlighting his commitment to high-quality imaging and creativity.",
    "Photo of a 30-year-old professional photographer, intense focus evident in his gaze, capturing a perfect shot in the vibrant streets of Berlin. He holds a sleek camera with innovative features, highlighting his commitment to high-quality imaging and creativity.",
  ];

  // Save fetched prompts
  setImageGenerationField({
    prompts,
  });
};
</script>

<template>
  <LandingColumn>
    <template #guidelines>
      <LandingPageGuideline class="hero-title">
        <template #title> Hero Title </template>

        Highlight the most attractive feature of your product. Use a bold,
        eye-catching headline to grab attention.
      </LandingPageGuideline>

      <LandingPageGuideline class="hero-subtitle">
        <template #title> Hero Subtitle </template>

        Add more context to the headline.
      </LandingPageGuideline>

      <LandingPageGuideline class="hero-paragraph">
        <template #title> Hero Paragraph </template>

        Explain how the product solves a problem or offers a unique benefit.
      </LandingPageGuideline>

      <LandingPageGuideline class="hero-cta">
        <template #title> Hero CTA </template>

        The main button should attract attention, inviting users to start.
      </LandingPageGuideline>

      <LandingPageGuideline class="hero-image">
        <template #title> Hero Image </template>

        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua.
      </LandingPageGuideline>
    </template>

    <LandingPageTitle class="hero-title">
      {{ values.heroTitle }}
    </LandingPageTitle>

    <LandingPageSubtitle class="hero-subtitle">
      {{ values.heroSubtitle }}
    </LandingPageSubtitle>

    <LandingPageParagraph class="hero-paragraph">
      {{ values.heroParagraph }}
    </LandingPageParagraph>

    <div class="hero-cta">
      <LandingPageCta>
        {{ values.heroCta }}
      </LandingPageCta>
    </div>

    <ImageGeneratorPreview name="heroImage" class="hero-image tw:aspect-square">
      Header Image
    </ImageGeneratorPreview>

    <template #modalTitle> Hero section </template>
    <template #modalDescription>
      Polish your hero section by adding a captivating header image, compelling
      headline, and a strong call-to-action to engage visitors instantly.
    </template>
    <template #modalBody>
      <EditableCardSection
        name="heroTitle"
        title="Hero Title"
        icon="tabler-pennant"
        iconVariant="primary"
        editable
      />

      <EditableCardSection
        name="heroSubtitle"
        title="Hero Subtitle"
        icon="tabler-building-skyscraper"
        iconVariant="gray"
        editable
      />

      <EditableCardSection
        name="heroParagraph"
        title="Hero Paragraph"
        icon="tabler-typography"
        iconVariant="success"
        editable
      />

      <EditableCardSection
        name="heroCta"
        title="Hero CTA"
        icon="tabler-social"
        iconVariant="info"
        editable
      />
    </template>
    <template #modalRight>
      <ImageGenerator
        :name="imageGenerationFieldName"
        @generatePrompts="handleGeneratePrompts"
      >
        <template #title>Generate hero image prompts</template>
        <template #description>
          6 hero image prompts will be generated; please verify the accuracy of
          all the information before proceeding.
        </template>
      </ImageGenerator>
    </template>
  </LandingColumn>
</template>
