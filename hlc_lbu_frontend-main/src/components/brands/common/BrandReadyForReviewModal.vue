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
      {{ $t("brands.settings.success-modal.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.success-modal.description") }}
    </template>

    <template #actions="{ close }">
      <Button @click="close">
        {{ $t("global.continue") }}
      </Button>
    </template>
  </ModalGeneric>
</template>
