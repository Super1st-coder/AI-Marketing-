<script setup lang="ts">
defineProps<{ src: string }>();

const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    name="youtube-help-modal"
    maxWidth="1000px"
    :videoSrc="src"
  >
    <template #title>
      <slot name="title" />
    </template>

    <template #cancel>
      {{ $t("global.close") }}
    </template>
  </ModalGeneric>
</template>
