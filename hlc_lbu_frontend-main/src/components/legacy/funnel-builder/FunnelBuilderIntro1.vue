<script lang="ts" setup>
const store = useAdGenerationStore();
</script>

<template>
  <div class="tw:flex tw:flex-col tw:items-center tw:gap-[60px]">
    <div class="tw:max-w-[918px] tw:text-center">
      <WizardCardTitle>
        Welcome to your Marketing Funnel Builder
      </WizardCardTitle>

      <WizardCardParagraph>
        Create any type of marketing campaign tailored to your needs.
      </WizardCardParagraph>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-10 tw:lg:flex-row">
      <FeatureCard variant="primary" src="/images/clipboard.png">
        1. Choose your framework and <br />
        funnel type

        <template #paragraph>
          Select the best funnel framework, stage, and acquisition type (Paid,
          Organic, or Others) that align with your goals.
        </template>
      </FeatureCard>
      <FeatureCard variant="error" src="/images/magic-wand.png">
        2. Generate your campaign assets

        <template #paragraph>
          Automatically generate custom ads, landing pages, and email sequences
          based on your selections.
        </template>
      </FeatureCard>
      <FeatureCard variant="info" src="/images/gears.png">
        3. Prepare for execution

        <template #paragraph>
          Get campaign materials ready for handoff to freelancers or your team
          for execution.
        </template>
      </FeatureCard>
    </div>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <Button icon="tabler-arrow-narrow-right" @click="store.goNext">
        CONTINUE TO FUNNEL BUILDER
      </Button>
    </WizardCardActions>
  </div>
</template>
