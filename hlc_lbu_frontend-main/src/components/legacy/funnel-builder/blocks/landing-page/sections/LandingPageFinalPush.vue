<script lang="ts" setup>
import { LandingPage } from "@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/landing-page/landing-page.vue";
import { useFormValues } from "vee-validate";

const { value: values } = useFormValues<LandingPage>();

useMaxHeightCards(
  [".final-push-title", ".final-push-subtitle", ".final-push-cta"],
  [values],
);
</script>

<template>
  <LandingColumn type="footer">
    <template #guidelines>
      <LandingPageGuideline class="final-push-title">
        <template #title> Final Push Title </template>

        Reinforce urgency and value.
      </LandingPageGuideline>

      <LandingPageGuideline class="final-push-subtitle">
        <template #title> Final Push Subtitle </template>

        Highlight key benefits again — low rates, cashback, rewards, etc.
      </LandingPageGuideline>

      <LandingPageGuideline class="final-push-cta">
        <template #title>Value Proposition CTA</template>

        Use action-oriented text to get the user to apply.
      </LandingPageGuideline>
    </template>

    <LandingPageTitle class="final-push-title">
      {{ values.finalPushTitle }}
    </LandingPageTitle>

    <LandingPageSubtitle class="final-push-subtitle">
      {{ values.finalPushSubtitle }}
    </LandingPageSubtitle>

    <div class="final-push-cta">
      <LandingPageCta>
        {{ values.finalPushCta }}
      </LandingPageCta>
    </div>

    <template #modalTitle> Final push section </template>
    <template #modalBody>
      <EditableCardSection
        name="finalPushTitle"
        title="Final Push Title"
        icon="tabler-pennant"
        iconVariant="primary"
        editable
      />

      <EditableCardSection
        name="finalPushSubtitle"
        title="Final Push Subtitle"
        icon="tabler-building-skyscraper"
        iconVariant="gray"
        editable
      />

      <EditableCardSection
        name="finalPushCta"
        title="Final Push CTA"
        icon="tabler-social"
        iconVariant="info"
        editable
      />
    </template>
  </LandingColumn>
</template>
