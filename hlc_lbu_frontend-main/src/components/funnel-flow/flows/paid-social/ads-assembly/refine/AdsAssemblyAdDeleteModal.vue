<script setup lang="ts">
import { ModalGenericConfirmFn } from "@/components/modals/ModalGeneric.vue";

defineProps<{ confirmFn: ModalGenericConfirmFn }>();

const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <ModalGeneric v-model="isOpen" :maxWidth="600" :confirmFn="confirmFn">
    <template #title>
      {{ $t("funnel-flow.paid-social.ads.refine.delete-modal.title") }}
    </template>

    <template #description>
      {{ $t("funnel-flow.paid-social.ads.refine.delete-modal.description") }}
    </template>

    <template #continue>
      {{ $t("funnel-flow.paid-social.ads.refine.delete-modal.confirm") }}
    </template>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>
  </ModalGeneric>
</template>
