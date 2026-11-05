<script setup lang="ts">
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";

const { goBack, goNext } = useMultiStepFormContext<UmbrellaCampaignFormData>();
</script>

<template>
  <FormStepLayout>
    <template #stepper>
      <MultiStepFormStepper parentStepName="scene" />
    </template>

    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=h3RLoihDatg">
      <template #chip>
        {{ $t("umbrella-campaign.step-scene.tutorial.chip") }}
      </template>
      <template #title>
        {{ $t("umbrella-campaign.step-scene.tutorial.title") }}
      </template>
      <template #description>
        {{ $t("umbrella-campaign.step-scene.tutorial.description-1")
        }}<br /><br />

        <strong class="tw:text-primary-text"
          >{{
            $t("umbrella-campaign.step-scene.tutorial.description-2-strong")
          }} </strong
        ><br />
        {{ $t("umbrella-campaign.step-scene.tutorial.description-3")
        }}<br /><br />

        <strong class="tw:text-primary-text">
          {{ $t("umbrella-campaign.step-scene.tutorial.description-4-strong") }}
        </strong>
      </template>
    </VideoTutorial>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext @click="goNext">
          {{ $t("umbrella-campaign.step-scene.tutorial.button") }}
        </ButtonNext>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
