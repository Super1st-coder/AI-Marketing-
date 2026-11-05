<script lang="ts" setup>
const store = useAdGenerationFirstPhaseStore();
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
    <FormHypothesis v-if="store.currentStep === 'hypothesis'" />
    <FormYourProduct v-else-if="store.currentStep === 'yourProduct'" />
    <FormYourProductRefinement
      v-else-if="store.currentStep === 'yourProductRefinement'"
    />
    <FormYourTarget v-else-if="store.currentStep === 'yourTarget'" />
    <FormYourTargetRefinement
      v-else-if="store.currentStep === 'yourTargetRefinement'"
    />
    <FormElement v-else-if="store.currentStep === 'element'" />
    <FormElementRefinement
      v-else-if="store.currentStep === 'elementRefinement'"
    />
    <FormGoal v-else-if="store.currentStep === 'goal'" />
    <FormGoalRefinement v-else-if="store.currentStep === 'goalRefinement'" />
    <FormBuyerChallenge v-else-if="store.currentStep === 'buyerChallenge'" />
    <FormBuyerChallengeRefinement
      v-else-if="store.currentStep === 'buyerChallengeRefinement'"
    />
  </WizardCard>
</template>
