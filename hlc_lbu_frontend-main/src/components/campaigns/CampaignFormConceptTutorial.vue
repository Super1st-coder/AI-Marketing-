<script setup lang="ts">
import { CampaignFormData } from "./CampaignForm.vue";

const { goBack, goNext } = useMultiStepFormContext<CampaignFormData>();
</script>

<template>
  <FormStepLayout>
    <template #stepper>
      <MultiStepFormStepper parentStepName="concept" />
    </template>

    <VideoTutorial>
      <template #chip>
        {{ $t("campaigns.videotutorial.chiptitle") }}
      </template>
      <template #title>
        {{ $t("campaigns.videotutorial.title") }}
      </template>
      <template #description>
        {{ $t("campaigns.videotutorial.description") }}
      </template>
    </VideoTutorial>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext @click="goNext" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
