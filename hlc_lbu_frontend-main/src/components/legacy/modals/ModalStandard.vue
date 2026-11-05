<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <Modal
    v-model="isOpen"
    innerClass="tw:px-5 tw:py-10 tw:lg:px-16 tw:max-w-[1156px] tw:flex-col tw:gap-[30px] tw:flex"
    closeButton
  >
    <div
      class="tw:flex tw:flex-col tw:gap-5 tw:lg:flex-row tw:lg:gap-10 tw:xl:gap-36"
    >
      <div class="tw:grow">
        <div class="tw:max-w-[600px]">
          <slot name="header" />
        </div>
      </div>

      <div
        class="tw:flex tw:max-w-[400px] tw:grow tw:items-center tw:justify-end tw:gap-5"
      >
        <slot name="headerActions" />
      </div>
    </div>

    <Separator />

    <div
      :class="{
        'tw:flex tw:flex-col tw:gap-[30px] tw:lg:flex-row tw:lg:gap-10':
          $slots.right,
      }"
    >
      <div :class="{ 'tw:basis-1/2': $slots.right }">
        <slot name="body" />
      </div>

      <div v-if="$slots.right">
        <Separator type="vertical" class="tw:hidden tw:lg:block" />
        <Separator type="horizontal" class="tw:lg:hidden" />
      </div>

      <div class="tw:basis-1/2" v-if="$slots.right">
        <slot name="right" />
      </div>
    </div>
  </Modal>
</template>
