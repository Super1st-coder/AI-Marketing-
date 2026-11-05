<script setup lang="ts">
const metaAdsConnection = metaAdsConnectionStore();
const adsConnection = adsConnectionStore();

const { currentFlatStepIndex, goToStep, goBack } = useMultiStepFormContext();

async function chooseObjective(objective: string) {
  metaAdsConnection.setCampaignObjective(objective);
  const currentStepIndex = currentFlatStepIndex.value;
  goToStep(currentStepIndex + 2);
}
</script>

<template>
  <FormStepLayout>
    <h1 class="tw:mb-0 tw:text-4xl tw:font-bold">Choose Your Objective</h1>
    <p class="tw:text-secondary">
      Select the objective that aligns with your media strategy.
    </p>
    <hr class="tw:border-secondary/30" />
    <div
      v-if="adsConnection.connection === 'meta-ads'"
      class="tw:grid tw:gap-[18px] tw:lg:grid-cols-3"
    >
      <FunnelFlowHomeCard icon="tabler:target-arrow">
        <template #title>Outcome Sales</template>

        <template #description>
          Increase conversions and generate more sales.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="chooseObjective('OUTCOME_SALES')"
          >
            Select
          </Button>
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:target-arrow">
        <template #title>Outcome Awareness</template>

        <template #description>
          Reach more unique users and boost brand visibility.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="chooseObjective('OUTCOME_AWARENESS')"
            >Select</Button
          >
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:target-arrow">
        <template #title>Outcome Traffic</template>

        <template #description>
          Drive more users to your site or content.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="chooseObjective('OUTCOME_TRAFFIC')"
          >
            Select
          </Button>
        </template>
      </FunnelFlowHomeCard>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
