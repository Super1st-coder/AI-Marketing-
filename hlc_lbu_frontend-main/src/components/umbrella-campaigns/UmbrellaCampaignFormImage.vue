<script lang="ts" setup>
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";

const { goBack, goToStep, data } =
  useMultiStepFormContext<UmbrellaCampaignFormData>();

const showModal = ref(false);

// Set the current screen based on the data
const currentScreen = ref<
  undefined | "upload" | "tutorial" | "createStyle" | "createPrompt"
>();

// Initialize currentScreen based on existing data
if (
  data.value.image_attributes_generated &&
  Object.keys(data.value.image_attributes_generated).length > 0
) {
  currentScreen.value = "createPrompt";
} else if (data.value.thumbnail_url) {
  currentScreen.value = "upload";
}

const handleSkip = () => {
  showModal.value = true;
};
</script>

<template>
  <FormStepLayout v-if="currentScreen === undefined">
    <ModalSkipCampaignImage
      v-model="showModal"
      @confirm="goToStep(14)"
      @cancel="showModal = false"
    />

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=uB81rH44TZU"
    >
      {{ $t("umbrella-campaign.step-image.title") }}
      <template #description>
        {{ $t("umbrella-campaign.step-image.description") }}
      </template>
    </PageTitle>

    <CardGrid>
      <SuggestionCard imageSrc="/images/emoji-painting.png">
        <template #title>
          {{ $t("umbrella-campaign.step-image.upload-title") }}
        </template>
        <template #description>
          {{ $t("umbrella-campaign.step-image.upload-description") }}
        </template>
        <template #action>
          <Button type="button" @click="currentScreen = 'upload'">
            {{ $t("umbrella-campaign.step-image.upload-action") }}
          </Button>
        </template>
      </SuggestionCard>
      <SuggestionCard imageSrc="/images/emoji-brush.png">
        <template #title>
          {{ $t("umbrella-campaign.step-image.ai-title") }}
        </template>
        <template #description>
          {{ $t("umbrella-campaign.step-image.ai-description") }}
        </template>
        <template #action>
          <Button type="button" @click="currentScreen = 'tutorial'">
            {{ $t("umbrella-campaign.step-image.ai-action") }}
          </Button>
        </template>
      </SuggestionCard>
    </CardGrid>
    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" type="button" />
        <ButtonNext @click="handleSkip" type="button">
          {{ $t("global.skip") }}
        </ButtonNext>
      </WizardCardActions>
    </template>
  </FormStepLayout>

  <UmbrellaCampaignFormImageUpload
    v-if="currentScreen === 'upload'"
    @goBack="currentScreen = undefined"
  />

  <UmbrellaCampaignFormImageTutorial
    v-if="currentScreen === 'tutorial'"
    @goBack="currentScreen = undefined"
    @goNext="currentScreen = 'createStyle'"
  />

  <UmbrellaCampaignFormImageCreateStyle
    v-if="currentScreen === 'createStyle'"
    @goBack="currentScreen = 'tutorial'"
    @goNext="currentScreen = 'createPrompt'"
  />

  <UmbrellaCampaignFormImageCreatePrompt
    v-if="currentScreen === 'createPrompt'"
    @goBack="currentScreen = 'createStyle'"
  />
</template>
