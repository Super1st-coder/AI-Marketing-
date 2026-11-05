<script setup lang="ts">
import { FunnelPaidSocialFormData } from "../FunnelPaidSocialForm.vue";

const store = useFunnelPaidSocialFormStore();
const { goNext } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const dontShowAgain = ref(!store.showAdsTutorial);

function handleContinue() {
  store.showAdsTutorial = !dontShowAgain.value;
  goNext();
}
</script>

<template>
  <FormStepLayout>
    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=r1462xlXJOQ">
      <template #chip>
        {{ $t("funnel-flow.paid-social.ads.tutorial.chip") }}
      </template>

      <template #title>
        {{ $t("funnel-flow.paid-social.ads.tutorial.title") }}
      </template>

      <template #description>
        {{ $t("funnel-flow.paid-social.ads.tutorial.description") }}
      </template>

      <template #actions>
        <Button @click="handleContinue" :uppercase="false">
          {{ $t("funnel-flow.paid-social.ads.tutorial.button") }}
        </Button>

        <FieldBaseCheckbox
          v-model="dontShowAgain"
          name="dont-show-ads-tutorial"
          :label="$t('global.dont-show-this-message-again')"
          class="tw:justify-center tw:font-normal"
        />
      </template>
    </VideoTutorial>
  </FormStepLayout>
</template>
