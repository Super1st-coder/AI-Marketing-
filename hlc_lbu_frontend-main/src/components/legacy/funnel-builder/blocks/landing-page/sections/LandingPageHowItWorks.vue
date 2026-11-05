<script lang="ts" setup>
import { LandingPage } from "@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/landing-page/landing-page.vue";
import { useFormValues } from "vee-validate";

const { value: values } = useFormValues<LandingPage>();

useMaxHeightCards(
  [
    ".how-it-works-title",
    ".how-it-works-subtitle",
    ".how-it-works-steps",
    ".how-it-works-paragraph",
    ".how-it-works-cta",
  ],
  [values],
);
</script>

<template>
  <LandingColumn>
    <template #guidelines>
      <LandingPageGuideline class="how-it-works-title">
        <template #title> How It Works Title </template>

        Explain the process in a simplified way, breaking it down into easy
        steps.
      </LandingPageGuideline>

      <LandingPageGuideline class="how-it-works-subtitle">
        <template #title> How It Works Subtitle </template>

        Explain the benefits of using the product or how simple it is to sign
        up.
      </LandingPageGuideline>

      <LandingPageGuideline class="how-it-works-steps">
        <template #title> How It Works Steps </template>

        Guide users through a streamlined process: from an easy sign-up, to
        quick approval, and seamless access to key benefits.
      </LandingPageGuideline>

      <LandingPageGuideline class="how-it-works-paragraph">
        <template #title> How It Works Paragraph </template>

        Explain the benefits of using the product or how simple it is to sign
        up.
      </LandingPageGuideline>

      <LandingPageGuideline class="how-it-works-cta">
        <template #title>How It Works CTA</template>

        Use action-oriented text to get the user to apply.
      </LandingPageGuideline>
    </template>

    <LandingPageTitle class="how-it-works-title">
      {{ values.howItWorksTitle }}
    </LandingPageTitle>

    <LandingPageSubtitle class="how-it-works-subtitle">
      {{ values.howItWorksSubtitle }}
    </LandingPageSubtitle>

    <div class="how-it-works-steps tw:flex tw:flex-col tw:gap-8">
      <LandingPageHowItWorksStep
        v-for="(value, index) in values.howItWorksSteps"
      >
        <template #title>Step {{ index + 1 }}</template>
        {{ value }}
      </LandingPageHowItWorksStep>
    </div>

    <LandingPageParagraph variant="light" class="how-it-works-paragraph">
      {{ values.howItWorksParagraph }}
    </LandingPageParagraph>

    <div class="how-it-works-cta">
      <LandingPageCta>
        {{ values.howItWorksCta }}
      </LandingPageCta>
    </div>

    <template #modalTitle> How it works section </template>
    <template #modalBody>
      <EditableCardSection
        name="howItWorksTitle"
        title="How It Works Title"
        icon="tabler-pennant"
        iconVariant="primary"
        editable
      />

      <EditableCardSection
        name="howItWorksSubtitle"
        title="How It Works Subtitle"
        icon="tabler-building-skyscraper"
        iconVariant="gray"
        editable
      />

      <EditableCardSection
        name="howItWorksSteps"
        title="How It Works Steps"
        icon="tabler-list"
        iconVariant="info"
        editable
      />

      <EditableCardSection
        name="howItWorksParagraph"
        title="How It Works Paragraph"
        icon="tabler-typography"
        iconVariant="success"
        editable
      />

      <EditableCardSection
        name="howItWorksCta"
        title="How It Works CTA"
        icon="tabler-social"
        iconVariant="info"
        editable
      />
    </template>
  </LandingColumn>
</template>
