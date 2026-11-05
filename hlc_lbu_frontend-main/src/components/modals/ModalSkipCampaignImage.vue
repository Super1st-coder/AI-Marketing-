<script setup lang="ts">
import Modal from "./base/Modal.vue";

const isTryingToBeOpened = defineModel<boolean>({ required: true });

const emit = defineEmits(["confirm", "cancel"]);

const handleConfirm = () => {
  emit("confirm");
  isTryingToBeOpened.value = false;
};

const handleCancel = () => {
  emit("cancel");
  isTryingToBeOpened.value = false;
};
</script>

<template>
  <Modal
    v-model="isTryingToBeOpened"
    innerClass="tw:w-full tw:max-w-[660px] tw:h-[410px] tw:p-6 tw:flex tw:flex-col    "
    :closeButton="false"
  >
    <div
      class="tw:flex tw:grow tw:flex-col tw:items-center tw:justify-center tw:gap-8 tw:overflow-y-auto"
    >
      <div class="tw:flex tw:flex-col tw:items-center tw:gap-2 tw:text-center">
        <img
          src="/images/emoji-alert.png"
          class="tw:mb-2 tw:h-[120px] tw:w-[580px] tw:max-w-full tw:object-contain"
        />
        <h2 class="tw:text-2xl tw:font-bold">
          {{ $t("umbrella-campaign.step-image.modal-skip.title") }}
        </h2>
        <p class="tw:mt-2 tw:text-base tw:text-gray-600">
          {{ $t("umbrella-campaign.step-image.modal-skip.description") }}
        </p>
      </div>
      <div class="tw:mt-auto tw:flex tw:w-full tw:justify-center tw:gap-4">
        <Button
          @click="handleCancel"
          variant="outlined"
          class="tw:bg-gray-200 tw:px-6 tw:py-2 tw:text-base tw:text-gray-700 tw:hover:bg-gray-300"
          >{{ $t("global.cancel") }}</Button
        >
        <Button
          @click="handleConfirm"
          class="tw:bg-blue-500 tw:px-6 tw:py-2 tw:text-base tw:text-white tw:hover:bg-blue-600"
          >{{ $t("umbrella-campaign.step-image.modal-skip.confirm") }}</Button
        >
      </div>
    </div>
  </Modal>
</template>
