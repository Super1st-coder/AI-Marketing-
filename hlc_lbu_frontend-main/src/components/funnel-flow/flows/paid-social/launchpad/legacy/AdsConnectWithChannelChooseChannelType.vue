<script setup lang="ts">
const adsConnection = adsConnectionStore();
const googleAdsConnection = googleAdsConnectionStore();

const { goNext, goBack, currentFlatStepIndex, goToStep } =
  useMultiStepFormContext();

async function chooseChannelType(channel: CampaignChannelType) {
  googleAdsConnection.setChannelType(channel);
  goNext();
}

function goBackChannelType() {
  const currentStepIndex = currentFlatStepIndex.value;
  if (adsConnection.connection === "google-ads") {
    goToStep(currentStepIndex - 2);
  } else if (adsConnection.connection === "meta-ads") {
    goBack();
  }
}
</script>

<template>
  <FormStepLayout>
    <h1 class="tw:mb-0 tw:text-4xl tw:font-bold">Choose Your Channel Type</h1>
    <p class="tw:text-secondary">
      Select the channel type that aligns with your objective.
    </p>
    <hr class="tw:border-secondary/30" />
    <div
      v-if="adsConnection.connection === 'google-ads'"
      class="tw:grid tw:gap-[18px] tw:lg:grid-cols-3"
    >
      <FunnelFlowHomeCard icon="ic:round-people-alt">
        <template #title>Display</template>

        <template #description>
          Reach as many unique users as possible. Great for broad exposure.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="chooseChannelType(CampaignChannelType.DISPLAY)"
            >Select</Button
          >
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:chart-area-line">
        <template #title>Performance Max</template>

        <template #description>
          Maximize ad views—even if users see it more than once.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="chooseChannelType(CampaignChannelType.PERFORMANCE_MAX)"
          >
            Select
          </Button>
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:chart-area-line">
        <template #title>Discovery</template>

        <template #description>
          Maximize ad views—even if users see it more than once.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            type="button"
            @click="chooseChannelType(CampaignChannelType.DISCOVERY)"
          >
            Select
          </Button>
        </template>
      </FunnelFlowHomeCard>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBackChannelType" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
