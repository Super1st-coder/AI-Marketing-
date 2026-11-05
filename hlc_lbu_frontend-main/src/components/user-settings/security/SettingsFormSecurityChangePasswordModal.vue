<script setup lang="ts">
const isTryingToBeOpened = defineModel<boolean>({ required: true });

const { t } = useI18n();

const emit = defineEmits(["confirm", "cancel"]);

const handleConfirm = () => {
  emit("confirm");
  isTryingToBeOpened.value = false;
};
</script>

<template>
  <Modal
    v-model="isTryingToBeOpened"
    innerClass="tw:w-full tw:max-w-2xl tw:p-6"
    :closeButton="false"
  >
    <div class="tw:flex tw:flex-col tw:items-center tw:gap-8">
      <div class="tw:flex tw:flex-col tw:items-center tw:gap-2 tw:p-6">
        <h2 class="tw:text-center tw:text-2xl tw:font-bold">
          {{ t("settings.security.modal-title") }}
        </h2>
        <p class="tw:mt-2 tw:text-center tw:text-base tw:text-gray-600">
          {{ t("settings.security.modal-mesage") }}
        </p>
      </div>
      <div class="tw:flex tw:w-full tw:justify-center tw:gap-4">
        <Button
          @click="handleConfirm"
          class="tw:bg-blue-500 tw:px-6 tw:py-2 tw:text-base tw:text-white tw:hover:bg-blue-600"
        >
          {{ t("settings.security.modal-button") }}
        </Button>
      </div>
    </div>
  </Modal>
</template>
