<script lang="ts" setup>
const store = useAdGenerationStore();
</script>

<template>
  <WizardCard
    class="tw:flex tw:flex-col tw:items-center tw:gap-[60px]"
    paddingY="lg"
  >
    <div class="tw:text-center">
      <WizardCardTitle>
        {{ $t("process.first-phase-ready.title") }}
      </WizardCardTitle>

      <WizardCardParagraph class="tw:max-w-none">
        {{ $t("process.first-phase-ready.description") }}
      </WizardCardParagraph>
    </div>

    <h2 class="tw:text-xl tw:font-extrabold">
      {{ $t("process.first-phase-ready.what-happens-next.title") }}
    </h2>

    <p
      class="tw:text-center tw:whitespace-break-spaces tw:text-primary-text/60"
    >
      {{ $t("process.first-phase-ready.what-happens-next.paragraph-1") }}
      <br />
      <br />
      {{ $t("process.first-phase-ready.what-happens-next.paragraph-2") }}
      <br />
      <br />
      {{ $t("process.first-phase-ready.what-happens-next.paragraph-3") }}
    </p>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <WizardButtonNext @click="store.goNext" />
    </WizardCardActions>
  </WizardCard>
</template>
