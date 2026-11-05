<script setup lang="ts">
import { ModalGenericConfirmFn } from "@/components/modals/ModalGeneric.vue";

const props = defineProps<{
  saveFn: ModalGenericConfirmFn;
  /** LUCA that re-scoring charges; shown before saving when known (HL-2739). */
  cost?: number;
}>();

const isOpen = defineModel<boolean>({ required: true });
const dontShowAgain = defineModel<boolean>("dontShowAgain", {
  default: false,
});

async function handleSave() {
  dontShowAgain.value = dontShowAgain.value;
  await props.saveFn();
}
</script>

<template>
  <ModalGeneric v-model="isOpen" :confirmFn="handleSave">
    <template #title>
      {{ $t("funnel-flow.paid-social.ads.video.scripts.save-modal.title") }}
    </template>

    <CardBase class="tw:px-6 tw:py-4" borderRadius="sm" :shadow="false">
      <p class="tw:font-medium">
        {{
          $t("funnel-flow.paid-social.ads.video.scripts.save-modal.description")
        }}
      </p>

      <p class="tw:text-secondary-text">
        {{ $t("funnel-flow.paid-social.ads.video.scripts.save-modal.hint") }}
      </p>

      <p
        v-if="cost !== undefined"
        class="tw:mt-2 tw:font-semibold"
        data-testid="video-scripts-save-cost"
      >
        {{
          $t("funnel-flow.paid-social.ads.video.scripts.save-modal.cost", {
            cost,
          })
        }}
      </p>
    </CardBase>

    <template #footerBefore>
      <FieldBaseCheckbox
        v-model="dontShowAgain"
        name="dontShowAgain-ads-assembly-video-scripts-save"
        :label="$t('global.dont-show-this-message-again')"
      />
    </template>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>

    <template #continue>
      {{ $t("funnel-flow.paid-social.ads.video.scripts.save-modal.confirm") }}
    </template>
  </ModalGeneric>
</template>
