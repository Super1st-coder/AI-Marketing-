<script setup lang="ts">
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";

const { goBack, goNext } = useMultiStepFormContext<UmbrellaCampaignFormData>();
const { t } = useI18n();
</script>

<template>
  <FormStepLayout>
    <template #stepper>
      <MultiStepFormStepper parentStepName="benefit" />
    </template>

    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=HUAj5DwpfsA">
      <template #chip>
        {{ t("umbrella-campaign.step-benefit.tutorial.chip") }}
      </template>
      <template #title>
        {{ t("umbrella-campaign.step-benefit.tutorial.title") }}</template
      >
      <template #description>
        <strong class="tw:text-primary-text">
          {{
            t("umbrella-campaign.step-benefit.tutorial['description-1-strong']")
          }} </strong
        ><br />
        {{ t("umbrella-campaign.step-benefit.tutorial['description-2']")
        }}<br /><br />
        <strong class="tw:text-primary-text">
          {{
            t("umbrella-campaign.step-benefit.tutorial['description-3-strong']")
          }} </strong
        ><br />
        {{ t("umbrella-campaign.step-benefit.tutorial['description-4']") }}
      </template>
    </VideoTutorial>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext @click="goNext">
          {{ t("umbrella-campaign.step-benefit.tutorial.button") }}
        </ButtonNext>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
