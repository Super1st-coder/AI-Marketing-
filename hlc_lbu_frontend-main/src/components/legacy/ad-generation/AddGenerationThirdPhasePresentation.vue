<script lang="ts" setup>
import ThirdPhaseAudience from "@/services/legacy/ThirdPhaseAudience";

const store = useAdGenerationStore();
const projectId = store.projectId;

const isLoading = ref(false);

const handleGoNext = async () => {
  isLoading.value = true;

  // Generate
  const response = await ThirdPhaseAudience.generate(projectId);

  // Save data locally
  store.data.audience = response.data.audience;
  store.data.preferred_audience = undefined;

  store.goNext();
};
</script>

<template>
  <WizardCard
    class="tw:flex tw:flex-col tw:items-center tw:gap-[60px]"
    paddingY="lg"
  >
    <div class="tw:max-w-[918px] tw:text-center">
      <WizardCardTitle> Build your creative campaign strategy </WizardCardTitle>

      <WizardCardParagraph>
        Build audiences, craft creative concepts, and combine them into
        effective campaigns.
      </WizardCardParagraph>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-10 tw:lg:flex-row">
      <FeatureCard variant="primary" src="/images/dart.png">
        1. Build your audiences

        <template #paragraph>
          Select three distinct audiences to test your hypothesis and find the
          best fit for each.
        </template>
      </FeatureCard>

      <FeatureCard variant="error" src="/images/diamond.png">
        2. Create your creative concepts

        <template #paragraph>
          Create tailored creative concepts for each audience to maximize
          engagement and impact.
        </template>
      </FeatureCard>

      <FeatureCard variant="success" src="/images/documents.png">
        3. Build a unified presentation

        <template #paragraph>
          Combine your hypothesis, personas, products, and concepts into a
          cohesive presentation to guide your campaigns.
        </template>
      </FeatureCard>
    </div>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <Button
        icon="tabler-arrow-narrow-right"
        @click="handleGoNext"
        :isLoading="isLoading"
      >
        CONTINUE TO CREATIVE CONCEPT BUILDER
      </Button>
    </WizardCardActions>
  </WizardCard>
</template>
