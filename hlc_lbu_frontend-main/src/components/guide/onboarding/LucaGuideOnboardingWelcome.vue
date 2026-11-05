<script setup lang="ts">
const store = useLucaGuideLayoutStore();
const { goNext } = useMultiStepFormContext();

const dontShowAgain = ref(!store.showTutorial);

function handleContinue() {
  store.showTutorial = !dontShowAgain.value;
  goNext();
}
</script>

<template>
  <FormStepLayout as="div" :maxWidth="1160">
    <template #stepper>
      <MultiStepFormStepper />
    </template>

    <VideoTutorial>
      <template #chip>
        {{ $t("luca-guide.onboarding.welcome.chip") }}
      </template>

      <template #title>
        {{ $t("luca-guide.onboarding.welcome.title") }}
      </template>

      <template #description>
        {{ $t("luca-guide.onboarding.welcome.description") }}
      </template>

      <template #actions>
        <Button @click="handleContinue">
          {{ $t("luca-guide.onboarding.welcome.button") }}
        </Button>

        <FieldBaseCheckbox
          v-model="dontShowAgain"
          name="dont-show-tutorial"
          :label="$t('global.dont-show-this-message-again')"
          class="tw:justify-center tw:font-normal"
        />
      </template>
    </VideoTutorial>
  </FormStepLayout>
</template>
