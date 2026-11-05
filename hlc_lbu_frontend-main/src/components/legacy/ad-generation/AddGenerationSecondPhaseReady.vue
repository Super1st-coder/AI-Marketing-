<script lang="ts" setup>
const store = useAdGenerationStore();
</script>

<template>
  <WizardCard
    class="tw:flex tw:flex-col tw:items-center tw:gap-[60px]"
    paddingY="lg"
  >
    <div class="tw:text-center">
      <WizardCardTitle class="tw:max-w-[450px]">
        {{ $t("process.second-phase-ready.title") }}
      </WizardCardTitle>

      <WizardCardParagraph class="tw:max-w-none">
        {{ $t("process.second-phase-ready.description") }}
      </WizardCardParagraph>
    </div>

    <Card padding="lg" class="tw:flex tw:max-w-[680px] tw:flex-col tw:gap-4">
      <h2 class="tw:text-xl tw:font-extrabold">
        {{ $t("process.second-phase-ready.card.title") }}
      </h2>

      <p>
        {{ $t("process.second-phase-ready.card.paragraph-1") }}
      </p>

      <p>
        {{ $t("process.second-phase-ready.card.paragraph-2") }}
      </p>

      <p class="tw:text-xl tw:font-extrabold">
        {{ $t("process.second-phase-ready.card.last-line") }}
      </p>
    </Card>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext @click="store.goNext" />
    </WizardCardActions>
  </WizardCard>
</template>
