<script setup lang="ts">
defineProps<{
  beforeSubmitFn?: () => Promise<void>;
  afterSubmitFn?: () => Promise<void>;
}>();

const isModalOpen = ref(false);
</script>

<template>
  <Alert type="warning">
    {{ $t("brands.settings.incomplete-information-alert.title") }}

    <template #actions>
      <Button
        type="button"
        size="sm"
        leftIcon="tabler:refresh"
        @click="isModalOpen = true"
      >
        {{ $t("brands.settings.incomplete-information-alert.action") }}
      </Button>
    </template>

    <BrandFormAddContextModal
      v-if="isModalOpen"
      v-model="isModalOpen"
      section="all"
      :loaderInterval="BRAND_NEW_CONTEXT_RING_LOADER_INTERVAL_MS"
      :loaderSteps="[
        $t('brands.settings.context-modal.all.loader-steps.0'),
        $t('brands.settings.context-modal.all.loader-steps.1'),
        $t('brands.settings.context-modal.all.loader-steps.2'),
        $t('brands.settings.context-modal.all.loader-steps.3'),
      ]"
      :beforeSubmitFn="beforeSubmitFn"
      :afterSubmitFn="afterSubmitFn"
    >
      <template #title>
        {{ $t("brands.settings.context-modal.all.title") }}
      </template>

      <template #description>
        {{ $t("brands.settings.context-modal.all.description") }}
      </template>
    </BrandFormAddContextModal>
  </Alert>
</template>
