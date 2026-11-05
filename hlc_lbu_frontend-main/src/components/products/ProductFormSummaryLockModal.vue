<script setup lang="ts">
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
    class="tw:w-full tw:max-w-[660px] tw:p-10"
    closeButton
  >
    <div class="tw:flex tw:flex-col tw:items-center tw:gap-8">
      <div class="tw:flex tw:flex-col tw:items-center tw:gap-3">
        <img src="/images/emoji-alert.png" class="tw:mb-2 tw:h-12 tw:w-auto" />
        <h2 class="tw:text-center tw:text-2xl tw:font-bold">
          {{ $t("products.summary.lock-modal.title") }}
        </h2>
        <p class="tw:mt-2 tw:text-center tw:text-base tw:text-gray-600">
          {{ $t("products.summary.lock-modal.paragraph-1") }}
        </p>
        <p class="tw:mt-2 tw:text-center tw:text-base tw:text-gray-600">
          {{ $t("products.summary.lock-modal.paragraph-2") }}
        </p>
      </div>

      <div
        class="tw:grid tw:gap-4 tw:md:grid-cols-2 tw:md:gap-8 tw:lg:px-[30px]"
      >
        <Button @click="handleConfirm">
          {{ $t("products.summary.lock-modal.confirm") }}
        </Button>

        <Button
          @click="handleCancel"
          variant="outlined"
          class="tw:md:order-first"
        >
          {{ $t("products.summary.lock-modal.cancel") }}
        </Button>
      </div>
    </div>
  </Modal>
</template>
