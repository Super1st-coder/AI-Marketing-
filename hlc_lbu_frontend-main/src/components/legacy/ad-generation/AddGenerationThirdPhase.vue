<script lang="ts" setup>
const store = useAdGenerationThirdPhaseStore();
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
      <FormAudience v-if="store.currentStep === 'audience'" />
      <FormCreativeConceptIntro
        v-else-if="store.currentStep === 'creativeConceptIntro'"
      />
      <FormCreativeConceptDetails
        v-else-if="store.currentStep === 'creativeConceptDetails'"
      />
      <FormCreativeConceptRefinement
        v-else-if="store.currentStep === 'creativeConceptRefinement'"
      />
      <FormCreativeConcept
        v-else-if="store.currentStep === 'creativeConcept'"
      />
      <FormCampaignConcept
        v-else-if="store.currentStep === 'campaignConcept'"
      />
      <FunnelBuilderIntro1
        v-else-if="store.currentStep === 'funnelBuilderIntro1'"
      />
      <FunnelBuilderIntro2
        v-else-if="store.currentStep === 'funnelBuilderIntro2'"
      />
      <FormFunnelFramework
        v-else="store.currentStep === 'chooseFunnelFramework'"
      />

      <template #fallback>
        <CircleLoaderDefault />
      </template>
    </Suspense>
  </WizardCard>
</template>
