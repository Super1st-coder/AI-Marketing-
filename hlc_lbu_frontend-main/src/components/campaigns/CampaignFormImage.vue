<script lang="ts" setup>
import { CampaignFormData } from "./CampaignForm.vue";
//import { useI18n } from "vue-i18n";

//const { t } = useI18n();

const { goBack, goToStep, data } = useMultiStepFormContext<CampaignFormData>();

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
      @confirm="goToStep(15)"
      @cancel="showModal = false"
    />

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=rZD4x4M9540"
    >
      {{ $t("campaigns.campaignsimage.image.title") }}
      <template #description>
        {{ $t("campaigns.campaignsimage.image.description") }}
      </template>
    </PageTitle>

    <CardGrid>
      <SuggestionCard imageSrc="/images/emoji-painting.png">
        <template #title>
          {{ $t("campaigns.campaignsimage.image.uploadCard.title") }}</template
        >

        <template #description>
          {{ $t("campaigns.campaignsimage.image.uploadCard.description") }}
        </template>

        <template #action>
          <Button type="button" @click="currentScreen = 'upload'">
            {{ $t("campaigns.campaignsimage.image.uploadCard.action") }}
          </Button>
        </template>
      </SuggestionCard>

      <SuggestionCard imageSrc="/images/emoji-brush.png">
        <template #title>
          {{
            $t("campaigns.campaignsimage.image.createAICard.title")
          }}</template
        >

        <template #description>
          {{ $t("campaigns.campaignsimage.image.createAICard.description") }}
        </template>

        <template #action>
          <Button type="button" @click="currentScreen = 'tutorial'">
            {{ $t("campaigns.campaignsimage.image.createAICard.action") }}
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

  <CampaignFormImageUpload
    v-if="currentScreen === 'upload'"
    @goBack="currentScreen = undefined"
  />

  <CampaignFormImageTutorial
    v-if="currentScreen === 'tutorial'"
    @goBack="currentScreen = undefined"
    @goNext="currentScreen = 'createStyle'"
  />

  <CampaignFormImageCreateStyle
    v-if="currentScreen === 'createStyle'"
    name="imageCreateStyle"
    @goBack="currentScreen = 'tutorial'"
    @goNext="currentScreen = 'createPrompt'"
  />

  <CampaignFormImageCreatePrompt
    v-if="currentScreen === 'createPrompt'"
    @goBack="currentScreen = 'createStyle'"
  />
</template>
