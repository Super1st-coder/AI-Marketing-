<script setup lang="ts">
import { FunnelPaidSocialFormData } from "./FunnelPaidSocialForm.vue";

const store = useFunnelPaidSocialFormStore();
const { goNext } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const dontShowAgain = ref(!store.showStructureTutorial);

function handleContinue() {
  store.showStructureTutorial = !dontShowAgain.value;
  goNext();
}
</script>

<template>
  <FormStepLayout>
    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=js4olusGJ1I">
      <template #chip>
        {{ $t("funnel-flow.paid-social.structure-tutorial.chip") }}
      </template>

      <template #title>
        {{ $t("funnel-flow.paid-social.structure-tutorial.title") }}
      </template>

      <template #description>
        {{ $t("funnel-flow.paid-social.structure-tutorial.description") }}
      </template>

      <template #actions>
        <Button @click="handleContinue">
          {{
            $t(
              "funnel-flow.paid-social.structure-tutorial.actions.create-structure",
            )
          }}
        </Button>

        <FieldBaseCheckbox
          v-model="dontShowAgain"
          name="dont-show-structure-tutorial"
          :label="$t('global.dont-show-this-message-again')"
          class="tw:justify-center tw:font-normal"
        />
      </template>
    </VideoTutorial>
  </FormStepLayout>
</template>
