<script setup lang="ts">
interface Props {
  name: string;
}

const props = defineProps<Props>();

const { isModalOpen, handleContinue, dontShowAgain, handleCancel } =
  useConfirmModalContext(props.name);
</script>

<template>
  <Modal
    v-model="isModalOpen"
    class="tw:max-w-[660px] tw:p-10"
    closeButton
    useCustomClose
    @customClose="handleCancel"
  >
    <div class="tw:flex tw:flex-col tw:items-center tw:gap-6">
      <div class="tw:text-center">
        <template v-if="$slots.title">
          <h2 class="tw:mb-1 tw:text-[28px] tw:font-extrabold">
            <slot name="title" />
          </h2>
        </template>

        <template v-if="$slots.description">
          <p class="tw:text-secondary-text">
            <slot name="description" />
          </p>
        </template>
      </div>

      <Button @click="handleContinue">
        {{ $t("global.continue") }}
      </Button>

      <div class="tw:flex tw:items-center tw:gap-2">
        <input
          type="checkbox"
          :id="name"
          :name="name"
          class="tw:h-[18px] tw:w-[18px]"
          v-model="dontShowAgain"
        />

        <label :for="name">
          {{ $t("global.dont-show-this-message-again") }}
        </label>
      </div>
    </div>
  </Modal>
</template>
