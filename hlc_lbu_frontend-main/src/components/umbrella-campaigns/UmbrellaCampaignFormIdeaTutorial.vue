<script setup lang="ts">
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";

const { goBack, goNext } = useMultiStepFormContext<UmbrellaCampaignFormData>();
const { t } = useI18n();
</script>

<template>
  <FormStepLayout>
    <template #stepper>
      <MultiStepFormStepper parentStepName="bigIdea" />
    </template>

    <div class="tw:flex tw:flex-col tw:gap-16">
      <h1 class="tw:text-center tw:text-4xl tw:font-extrabold">
        {{ t("umbrella-campaign.step-big-idea.tutorial.title") }}
      </h1>

      <div class="tw:flex tw:flex-col tw:gap-6 tw:lg:flex-row">
        <UmbrellaCampaignFormIdeaTutorialCard
          imageSrc="/images/emojis/wrapped-present.png"
        >
          <template #title>
            {{ t("umbrella-campaign.step-big-idea.tutorial.step-1-title") }}
          </template>
          {{ t("umbrella-campaign.step-big-idea.tutorial.step-1-description") }}
        </UmbrellaCampaignFormIdeaTutorialCard>

        <UmbrellaCampaignFormIdeaTutorialCard
          imageSrc="/images/emojis/clapper-board.png"
        >
          <template #title>
            {{ t("umbrella-campaign.step-big-idea.tutorial.step-2-title") }}
          </template>
          {{ t("umbrella-campaign.step-big-idea.tutorial.step-2-description") }}
        </UmbrellaCampaignFormIdeaTutorialCard>

        <UmbrellaCampaignFormIdeaTutorialCard
          imageSrc="/images/emojis/performing-arts.png"
        >
          <template #title>
            {{ t("umbrella-campaign.step-big-idea.tutorial.step-3-title") }}
          </template>
          {{ t("umbrella-campaign.step-big-idea.tutorial.step-3-description") }}
        </UmbrellaCampaignFormIdeaTutorialCard>
      </div>

      <p class="tw:text-center tw:text-lg tw:font-extrabold">
        {{ t("umbrella-campaign.step-big-idea.tutorial.footer") }}
      </p>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext @click="goNext" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
