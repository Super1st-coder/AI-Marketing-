<script setup lang="ts">
export interface ModalRingLoaderProps {
  isReady?: boolean;
  steps: string[];
  interval?: number;
}

defineProps<ModalRingLoaderProps>();

const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="500"
    fallbackFocusToForeground
    class="tw:px-6 tw:py-8"
    :closeOnClickOutside="false"
  >
    <ProgressRingLoader
      :steps="steps"
      :completed="isReady"
      :interval="interval"
    >
      <template #title>
        <slot name="title" />
      </template>

      <template #description>
        <slot name="description" />
      </template>
    </ProgressRingLoader>
  </Modal>
</template>
