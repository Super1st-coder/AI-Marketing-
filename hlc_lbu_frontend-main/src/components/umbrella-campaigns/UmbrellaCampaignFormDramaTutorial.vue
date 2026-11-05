<script setup lang="ts">
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";
const { t } = useI18n();
const { goBack, goNext } = useMultiStepFormContext<UmbrellaCampaignFormData>();
</script>

<template>
  <FormStepLayout>
    <template #stepper>
      <MultiStepFormStepper parentStepName="drama" />
    </template>

    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=ghWYiqbDw9k">
      <template #chip>
        {{ t("umbrella-campaign.step-drama.tutorial.chip") }}
      </template>
      <template #title>
        {{ t("umbrella-campaign.step-drama.tutorial.title") }}
      </template>
      <template #description>
        {{ t("umbrella-campaign.step-drama.tutorial.desc-1") }}<br /><br />
        {{ t("umbrella-campaign.step-drama.tutorial.desc-2") }}<br /><br />
        <strong class="tw:text-primary-text">
          {{ t("umbrella-campaign.step-drama.tutorial.desc-3-strong") }}
        </strong>
        {{ t("umbrella-campaign.step-drama.tutorial.desc-3-rest") }}<br /><br />
        <strong class="tw:text-primary-text">
          {{ t("umbrella-campaign.step-drama.tutorial.desc-4") }}
        </strong>
      </template>
    </VideoTutorial>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext @click="goNext">
          {{ t("umbrella-campaign.step-drama.tutorial.button-next") }}
        </ButtonNext>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
