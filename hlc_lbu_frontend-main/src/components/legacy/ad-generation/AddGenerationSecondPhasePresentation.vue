<script lang="ts" setup>
import SecondPhaseBuyerPerson from "@/services/legacy/SecondPhaseBuyerPerson";

const store = useAdGenerationStore();

const isLoading = ref(false);

const handleGoNext = async () => {
  isLoading.value = true;

  // Initialize refination
  await SecondPhaseBuyerPerson.initializeProjectRefination(store.projectId);

  // Generate buyer persons
  const responsePersons = await SecondPhaseBuyerPerson.generate(
    store.projectId,
  );

  // Save data from response
  store.data.buyer_persons = responsePersons.data?.buyer_persons;

  store.goNext();
};
</script>

<template>
  <WizardCard
    class="tw:flex tw:flex-col tw:items-center tw:gap-[60px]"
    paddingY="lg"
  >
    <div class="tw:max-w-[918px] tw:text-center">
      <WizardCardTitle>
        {{ $t("process.second-phase-presentation.title") }}
      </WizardCardTitle>

      <WizardCardParagraph>
        {{ $t("process.second-phase-presentation.description") }}
      </WizardCardParagraph>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-10 tw:lg:flex-row">
      <FeatureCard variant="primary" src="/images/dart.png">
        {{ $t("process.second-phase-presentation.cards.target-buyer.title") }}

        <template #paragraph>
          {{
            $t(
              "process.second-phase-presentation.cards.target-buyer.description",
            )
          }}
        </template>
      </FeatureCard>
      <FeatureCard variant="error" src="/images/diamond.png">
        {{ $t("process.second-phase-presentation.cards.your-product.title") }}

        <template #paragraph>
          {{
            $t(
              "process.second-phase-presentation.cards.your-product.description",
            )
          }}
        </template>
      </FeatureCard>
      <FeatureCard variant="success" src="/images/documents.png">
        {{
          $t("process.second-phase-presentation.cards.your-hypothesis.title")
        }}

        <template #paragraph>
          {{
            $t(
              "process.second-phase-presentation.cards.your-hypothesis.description",
            )
          }}
        </template>
      </FeatureCard>
    </div>

    <WizardCardActions>
      <WizardButtonGoBack @click="store.goBack" />

      <Button
        icon="tabler-arrow-narrow-right"
        class="tw:basis-[515px]"
        @click="handleGoNext"
        :isLoading="isLoading"
      >
        LET’S GET STARTED
      </Button>
    </WizardCardActions>
  </WizardCard>
</template>
