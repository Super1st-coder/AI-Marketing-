<script setup lang="ts">
import ModalRingLoader, {
  type ModalRingLoaderProps,
} from "@/components/modals/ModalRingLoader.vue";

const props = defineProps<ModalRingLoaderProps>();

const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <ModalRingLoader v-model="isOpen" v-bind="props">
    <template #title>
      {{ $t("brands.create.upload-modal.loading-title") }}
    </template>

    <template #description>
      {{ $t("brands.create.upload-modal.loading-description") }}
    </template>
  </ModalRingLoader>
</template>
