<script setup lang="ts">
import { ImgFileProps } from "../images/ImgFile.vue";
import { ModalGenericConfirmFn } from "./ModalGeneric.vue";

const props = defineProps<{
  confirmFn: ModalGenericConfirmFn;
  imgSrc?: ImgFileProps["src"];
}>();

const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    :confirmFn="props.confirmFn"
    :continueButtonProps="{ color: 'error' }"
  >
    <template v-if="$slots.title" #title>
      <slot name="title" />
    </template>

    <template v-if="$slots.description" #description>
      <slot name="description" />
    </template>

    <Alert v-if="$slots.warning" type="warning">
      <slot name="warning">
        {{ $t("modals.delete.this-action-cannot-be-undone") }}
      </slot>
    </Alert>

    <div v-if="imgSrc" class="tw:flex tw:justify-center">
      <ImgFile
        :src="imgSrc"
        class="tw:rounded-2xl tw:object-contain"
        style="max-height: 200px"
      />
    </div>

    <slot name="after" />

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>

    <template #continue>
      {{ $t("modals.delete.yes-delete") }}
    </template>
  </ModalGeneric>
</template>
