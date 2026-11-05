<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    imageSrc="/images/celebrar-image.png"
    :maxWidth="500"
    variant="centered"
  >
    <template #title>
      {{ $t("campaigns.summary.modal.title") }}
    </template>

    <template #description>
      {{ $t("campaigns.summary.modal.description") }}
    </template>

    <template #actions="{ close }">
      <Button color="secondary" variant="outlined" @click="close">
        {{ $t("campaigns.summary.modal.back-to-campaign") }}
      </Button>

      <Button :to="{ name: 'FunnelFlowHome' }">
        {{ $t("campaigns.summary.modal.create-meta-ads") }}
      </Button>
    </template>
  </ModalGeneric>
</template>
