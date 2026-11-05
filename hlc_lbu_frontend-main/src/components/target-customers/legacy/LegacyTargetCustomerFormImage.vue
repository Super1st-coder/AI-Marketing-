<script lang="ts" setup>
import BuyerPersonasApi from "@/services/BuyerPersonasApi";
import { TargetCustomerFormData } from "../TargetCustomerForm.vue";
import { LlmOutputError } from "@/services/common-errors";

const { t } = useI18n();

const brandId = useBrandId();
const { data, goBack, goNext, saveData, getIsStageDirty, setDirtyStage } =
  useMultiStepFormContext<TargetCustomerFormData>();

const { confirm } = useConfirmModal();

// Set the current screen based on the data
const currentScreen = ref<undefined | "upload" | "create">();
if (
  data.value.image_attributes_generated &&
  Object.keys(data.value.image_attributes_generated).length > 0
) {
  currentScreen.value = "create";
} else if (data.value.thumbnail_url) {
  currentScreen.value = "upload";
}

const closeScreen = () => {
  currentScreen.value = undefined;
};

const handleUpload = async () => {
  currentScreen.value = "upload";
};

const isLoading = ref(false);
const generalErrorMessage = ref<string>();

const handleGenerate = async () => {
  try {
    generalErrorMessage.value = undefined;
    isLoading.value = true;

    let triggerGeneration = true;

    // Display and wait for the confirm modal if needed
    if (data.value.image_attributes_generated) {
      if (getIsStageDirty("image")) {
        // Display the modal if the data is dirty
        const result = await confirm();
        if (result === "close") {
          return;
        }

        triggerGeneration = result === "continue";
      } else {
        // If the data is not dirty, do not trigger prompts
        triggerGeneration = false;
      }
    }

    // Generate image attributes
    const response = await BuyerPersonasApi.generateImageAttributes(
      brandId,
      data.value.id,
      { trigger_prompts: triggerGeneration },
    );

    // Save the generated attributes
    setDirtyStage("image", false);
    saveData({ ...response.data });
    isLoading.value = false;

    // Show the create screen
    currentScreen.value = "create";
  } catch (error) {
    if (error instanceof LlmOutputError) {
      generalErrorMessage.value = t(`errors.${error.message}.title`);
      isLoading.value = false;
    } else {
      throw error;
    }
  }
};
</script>

<template>
  <FormStepLayout
    v-if="currentScreen === undefined"
    :disabled="data.locked || isLoading"
  >
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=Kqw5Y6v0SoM"
    >
      {{ t("buyer-person.image.legacy.title") }}

      <template #description>
        {{ t("buyer-person.image.legacy.description") }}
      </template>
    </PageTitle>

    <CardGrid>
      <SuggestionCard imageSrc="/images/emoji-painting.png">
        <template #title>
          {{ t("buyer-person.image.legacy.upload.title") }}
        </template>

        <template #description>
          {{ t("buyer-person.image.legacy.upload.description") }}
        </template>

        <template #action>
          <Button type="button" @click="handleUpload">
            {{ t("global.upload") }}
          </Button>
        </template>
      </SuggestionCard>

      <SuggestionCard imageSrc="/images/emoji-brush.png">
        <template #title>
          {{ t("buyer-person.image.legacy.create.title") }}
        </template>

        <template #description>
          {{ t("buyer-person.image.legacy.create.description") }}
        </template>

        <template #action>
          <Button type="button" @click="handleGenerate" :isLoading="isLoading">
            {{ t("global.create") }}
          </Button>
        </template>
      </SuggestionCard>
    </CardGrid>

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext v-if="data.locked" @click="goNext({ isDirty: false })" />
      </WizardCardActions>
    </template>
  </FormStepLayout>

  <LegacyTargetCustomerFormImageUpload
    v-if="currentScreen === 'upload'"
    @goBack="closeScreen"
  />

  <LegacyTargetCustomerFormImageCreate
    v-if="currentScreen === 'create'"
    @goBack="closeScreen"
  />

  <ModalConfirmRegeneration />
</template>
