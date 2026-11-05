<script setup lang="ts">
import { ModalGenericProps } from "../ModalGeneric.vue";

const props = withDefaults(defineProps<ModalGenericProps>(), {
  name: "confirm",
});

const {
  isModalOpen,
  handleCancel,
  handleClose,
  handleContinue,
  dontShowAgain,
} = useConfirmModalContext(props.name);
</script>

<template>
  <ModalGeneric
    v-bind="props"
    v-model="isModalOpen"
    v-model:dontShowAgain="dontShowAgain"
    @cancel="handleCancel"
    @confirm="handleContinue"
    @close="handleClose"
  >
    <!-- Pass all the slots -->
    <template v-for="(_, name) in $slots" #[name]="scope">
      <slot :name v-bind="scope ?? {}" />
    </template>
  </ModalGeneric>
</template>
