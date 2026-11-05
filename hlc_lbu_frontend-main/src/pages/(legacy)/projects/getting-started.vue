<script lang="ts" setup></script>

<template>
  <WizardCard
    class="tw:flex tw:flex-col tw:items-center tw:gap-[60px]"
    paddingY="lg"
  >
    <div class="tw:text-center">
      <WizardCardTitle>
        {{ $t("process.getting-started.title") }}
      </WizardCardTitle>

      <WizardCardParagraph class="tw:whitespace-break-spaces">
        {{ $t("process.getting-started.description") }}
      </WizardCardParagraph>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-10 tw:lg:flex-row tw:lg:gap-36">
      <FeatureCard variant="primary" src="/images/dart.png">
        {{ $t("process.getting-started.define-your-buyer") }}
      </FeatureCard>
      <FeatureCard variant="error" src="/images/diamond.png">
        {{ $t("process.getting-started.define-your-product") }}
      </FeatureCard>
      <FeatureCard variant="info" src="/images/flag.png">
        {{ $t("process.getting-started.define-your-goal") }}
      </FeatureCard>
      <FeatureCard variant="success" src="/images/lightbulb.png">
        {{ $t("process.getting-started.create-your-growth-hypothesis") }}
      </FeatureCard>
    </div>

    <div class="tw:flex tw:justify-center tw:self-stretch">
      <Button
        icon="tabler-arrow-narrow-right"
        class="tw:basis-[505px]"
        :to="{ name: 'AdGenerationCreate' }"
      >
        {{ $t("process.getting-started.get-started") }}
      </Button>
    </div>
  </WizardCard>
</template>
