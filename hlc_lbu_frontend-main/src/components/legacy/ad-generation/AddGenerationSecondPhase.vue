<script lang="ts" setup>
const store = useAdGenerationSecondPhaseStore();
</script>

<template>
  <WizardCard class="tw:mb-[50px]">
    <WizardSteps
      :stages="store.stages"
      :currentStep="store.currentStep"
      @clickStage="store.goToStage"
    />
  </WizardCard>

  <WizardCard paddingY="lg">
    <Suspense timeout="0">
      <FormTargetBuyer v-if="store.currentStep === 'targetBuyer'" />
      <FormProduct v-else-if="store.currentStep === 'product'" />
      <FormYourHypothesis v-else="store.currentStep === 'yourHypothesis'" />

      <template #fallback>
        <CircleLoaderDefault />
      </template>
    </Suspense>
  </WizardCard>
</template>
