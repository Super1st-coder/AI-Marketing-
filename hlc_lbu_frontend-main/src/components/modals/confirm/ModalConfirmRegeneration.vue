<script setup lang="ts">
const { isModalOpen, handleCancel, handleContinue } = useConfirmModalContext();
</script>

<template>
  <Modal
    v-model="isModalOpen"
    class="tw:max-w-[660px] tw:p-10"
    :closeOnClickOutside="false"
  >
    <div class="tw:flex tw:flex-col tw:gap-3 tw:text-center">
      <div class="tw:flex tw:justify-center">
        <Icon
          icon="tabler:alert-triangle-filled"
          class="tw:text-9xl tw:text-warning"
        />
      </div>

      <h2 class="tw:text-center tw:text-[28px] tw:font-extrabold">
        {{ $t("confirm-regeneration-modal.title") }}
      </h2>

      <p>
        {{ $t("confirm-regeneration-modal.description") }}
      </p>
    </div>

    <div
      class="tw:mt-12 tw:grid tw:gap-4 tw:md:grid-cols-2 tw:md:gap-8 tw:lg:px-[30px]"
    >
      <Button type="button" @click="handleContinue">
        {{ $t("global.continue") }}
      </Button>

      <Button
        class="tw:md:order-first"
        @click="handleCancel"
        variant="outlined"
      >
        {{ $t("confirm-regeneration-modal.keep-previous") }}
      </Button>
    </div>
  </Modal>
</template>
