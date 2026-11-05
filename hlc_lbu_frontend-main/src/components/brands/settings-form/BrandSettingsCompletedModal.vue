<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    variant="centered"
    imageSrc="/images/celebrar-image.png"
    :maxWidth="500"
  >
    <template #title>
      {{ $t("brands.settings.completed-modal.title") }}
    </template>

    <template #description>
      {{ $t("brands.settings.completed-modal.description") }}
    </template>

    <Alert type="info">
      <i18n-t
        keypath="brands.settings.completed-modal.optimization-tip"
        tag="span"
      >
        <template #label>
          <strong>{{
            $t("brands.settings.completed-modal.optimization-tip-label")
          }}</strong>
        </template>
      </i18n-t>
    </Alert>

    <template #actions="{ close }">
      <Button
        color="secondary"
        variant="outlined"
        :uppercase="false"
        @click="close"
      >
        {{ $t("brands.settings.completed-modal.stay-and-add-more") }}
      </Button>

      <Button :to="{ name: 'Brand' }" :uppercase="false">
        {{ $t("brands.settings.completed-modal.go-to-workspace") }}
      </Button>
    </template>
  </ModalGeneric>
</template>
