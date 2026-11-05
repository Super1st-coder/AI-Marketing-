<script setup lang="ts">
const store = useFunnelPaidSocialFormStore();
const { goNext } = useMultiStepFormContext();
const { t } = useI18n();

const dontShowAgain = ref(!store.showLaunchpadTutorial);

function handleContinue() {
  store.showLaunchpadTutorial = !dontShowAgain.value;
  goNext();
}

async function resetMetaAuth() {
  await $api("/v2/external/facebook/reset_auth", {
    method: "GET",
  });

  goNext();
}

(window as any).resetMetaAuth = resetMetaAuth;
</script>

<template>
  <FormStepLayout>
    <template #stepper>
      <AdsLaunchpadStepper />
    </template>

    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=PS-LLZhhrJA">
      <template #chip>
        {{ $t("funnel-flow.paid-social.launchpad.tutorial.chip") }}
      </template>
      <template #title>
        {{ $t("funnel-flow.paid-social.launchpad.tutorial.title") }}
      </template>
      <template #description>
        {{ $t("funnel-flow.paid-social.launchpad.tutorial.description") }}
      </template>
      <template #actions>
        <Button type="button" @click="handleContinue">
          {{ t("funnel-flow.paid-social.launchpad.tutorial.go-to-launchpad") }}
        </Button>

        <FieldBaseCheckbox
          v-model="dontShowAgain"
          name="dont-show-launchpad-tutorial"
          :label="$t('global.dont-show-this-message-again')"
          class="tw:justify-center tw:font-normal"
        />
      </template>
    </VideoTutorial>
  </FormStepLayout>
</template>
