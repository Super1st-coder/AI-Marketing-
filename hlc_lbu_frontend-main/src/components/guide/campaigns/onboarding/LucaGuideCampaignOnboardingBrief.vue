<script setup lang="ts">
const router = useRouter();
const { goNext } = useMultiStepFormContext();

function handleGoBack() {
  router.push({ name: "LucaGuideCampaigns" });
}
</script>

<template>
  <FormStepLayout as="div" :maxWidth="1096">
    <template #stepper>
      <MultiStepFormStepper />
    </template>

    <PageTitle>
      {{ $t("luca-guide.campaigns.onboarding.brief.title") }}
      <template #description>
        {{ $t("luca-guide.campaigns.onboarding.brief.description") }}
      </template>

      <!-- TODO: add View Campaign Team button -->
    </PageTitle>

    <p class="tw:text-sm tw:text-gray-500">
      Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
      tempor incididunt ut labore et dolore magna aliqua.
    </p>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="handleGoBack" />
        <Button icon="tabler-arrow-right" @click="goNext">
          {{
            $t("luca-guide.campaigns.onboarding.continue-to-creative-strategy")
          }}
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
