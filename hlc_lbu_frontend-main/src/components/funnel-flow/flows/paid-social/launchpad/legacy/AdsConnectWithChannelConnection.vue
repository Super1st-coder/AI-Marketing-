<script setup lang="ts">
const { goNext, goBack } = useMultiStepFormContext();

const adsConnection = adsConnectionStore();

function setConnection(connection: Connection) {
  adsConnection.setConnection(connection);
  goNext();
}
</script>

<template>
  <FormStepLayout>
    <h1 class="tw:mb-0 tw:text-4xl tw:font-bold">
      Select a Platform to Active
    </h1>
    <p class="tw:text-secondary">
      Select the paid channel you want to activate with this campaign.
    </p>
    <hr class="tw:border-secondary/30" />
    <div class="tw:grid tw:gap-[18px] tw:lg:grid-cols-3">
      <FunnelFlowHomeCard icon="tabler:brand-meta">
        <template #title>Meta</template>

        <template #description>
          Meta campaigns reach 70%+ of internet users weekly. Ideal for
          retargeting, lead gen, and branded content.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            @click="() => setConnection('meta-ads')"
            >Select</Button
          >
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard icon="tabler:brand-google">
        <template #title>Google Ads</template>

        <template #description>Upload your campaigns to Google Ads.</template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            @click="() => setConnection('google-ads')"
            >Select</Button
          >
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard
        icon="tabler:brand-tiktok"
        class="tw:relative tw:opacity-70"
      >
        <template #title>TikTok</template>

        <template #description>
          <div
            class="tw:absolute tw:top-3 tw:right-3 tw:rounded-md tw:bg-secondary/20 tw:px-3 tw:py-1 tw:font-bold"
          >
            Soon
          </div>

          Launch creative-first campaigns on the #1 platform for attention and
          engagement among Gen Z and Millennials.
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            @click="
              () => {
                goNext();
              }
            "
            disabled
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
