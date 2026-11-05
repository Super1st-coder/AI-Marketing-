<script lang="ts" setup>
import { LandingPage } from "@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/landing-page/landing-page.vue";
import { useFormValues } from "vee-validate";

const { value: values } = useFormValues<LandingPage>();

useMaxHeightCards(
  [".trust-title", ".trust-paragraph", ".trust-testimonials"],
  [values],
);
</script>

<template>
  <LandingColumn>
    <template #guidelines>
      <LandingPageGuideline class="trust-title">
        <template #title> Trust Title </template>

        Showcase customer satisfaction and trust.
      </LandingPageGuideline>

      <LandingPageGuideline class="trust-paragraph">
        <template #title> Trust Paragraph </template>

        Highlight how users benefit from the product, focusing on specific
        outcomes.
      </LandingPageGuideline>

      <LandingPageGuideline class="trust-testimonials">
        <template #title> Trust Testiomonials </template>

        Use 3-4 customer quotes and include names or pictures for authenticity.
      </LandingPageGuideline>
    </template>

    <LandingPageTitle class="trust-title">
      {{ values.trustTitle }}
    </LandingPageTitle>

    <LandingPageParagraph variant="light" class="trust-paragraph">
      {{ values.trustParagraph }}
    </LandingPageParagraph>

    <div class="trust-steps tw:flex tw:flex-col tw:gap-8">
      <LandingPageTrustTestimonial
        v-for="(value, index) in values.trustTestimonials"
      >
        <template #title>Step {{ index + 1 }}</template>
        {{ value }}
      </LandingPageTrustTestimonial>
    </div>

    <template #modalTitle> Trust section </template>
    <template #modalBody>
      <EditableCardSection
        name="trustTitle"
        title="Trust Title"
        icon="tabler-pennant"
        iconVariant="primary"
        editable
      />

      <EditableCardSection
        name="trustParagraph"
        title="Trust Paragraph"
        icon="tabler-typography"
        iconVariant="success"
        editable
      />

      <EditableCardSection
        name="trustTestimonials"
        title="Trust Testimonials"
        icon="tabler-list"
        iconVariant="info"
        editable
      />
    </template>
  </LandingColumn>
</template>
