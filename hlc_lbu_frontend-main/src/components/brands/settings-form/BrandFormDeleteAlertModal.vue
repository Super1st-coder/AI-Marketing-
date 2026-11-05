<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    variant="centered"
    :maxWidth="500"
    imageSrc="/images/emojis/stop-sign.png"
  >
    <template #title>
      <slot name="title" />
    </template>

    <template #description>
      <slot name="description" />
    </template>

    <template #continue>
      {{ $t("brands.settings.delete-constraint.continue") }}
    </template>
  </ModalGeneric>
</template>
