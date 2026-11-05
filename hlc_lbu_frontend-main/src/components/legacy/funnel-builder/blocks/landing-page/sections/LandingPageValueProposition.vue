<script lang="ts" setup>
import { LandingPage } from "@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/landing-page/landing-page.vue";
import { useFormValues } from "vee-validate";

const { value: values } = useFormValues<LandingPage>();

useMaxHeightCards(
  [
    ".value-proposition-title",
    ".value-proposition-subtitle",
    ".value-proposition-paragraph",
    ".value-proposition-cta",
  ],
  [values],
);
</script>

<template>
  <LandingColumn>
    <template #guidelines>
      <LandingPageGuideline class="value-proposition-title">
        <template #title> Value Proposition Title </template>

        Describe how your product beats the competition.
      </LandingPageGuideline>

      <LandingPageGuideline class="value-proposition-subtitle">
        <template #title> Value Proposition Subtitle </template>

        Add more context to the headline.
      </LandingPageGuideline>

      <LandingPageGuideline class="value-proposition-paragraph">
        <template #title> Value Proposition Paragraph </template>

        Explain how the product solves a problem or offers a unique benefit.
      </LandingPageGuideline>

      <LandingPageGuideline class="value-proposition-cta">
        <template #title>Value Proposition CTA</template>

        Use action-oriented text to get the user to apply.
      </LandingPageGuideline>
    </template>

    <LandingPageTitle class="value-proposition-title">
      {{ values.valuePropositionTitle }}
    </LandingPageTitle>

    <LandingPageSubtitle class="value-proposition-subtitle">
      {{ values.valuePropositionSubtitle }}
    </LandingPageSubtitle>

    <LandingPageParagraph variant="light" class="value-proposition-paragraph">
      {{ values.valuePropositionParagraph }}
    </LandingPageParagraph>

    <div class="value-proposition-cta">
      <LandingPageCta>
        {{ values.valuePropositionCta }}
      </LandingPageCta>
    </div>

    <template #modalTitle> Value proposition section </template>
    <template #modalBody>
      <EditableCardSection
        name="valuePropositionTitle"
        title="Value Proposition Title"
        icon="tabler-pennant"
        iconVariant="primary"
        editable
      />

      <EditableCardSection
        name="valuePropositionSubtitle"
        title="Value Proposition Subtitle"
        icon="tabler-building-skyscraper"
        iconVariant="gray"
        editable
      />

      <EditableCardSection
        name="valuePropositionParagraph"
        title="Value Proposition Paragraph"
        icon="tabler-typography"
        iconVariant="success"
        editable
      />

      <EditableCardSection
        name="valuePropositionCta"
        title="Value Proposition CTA"
        icon="tabler-social"
        iconVariant="info"
        editable
      />
    </template>
  </LandingColumn>
</template>
