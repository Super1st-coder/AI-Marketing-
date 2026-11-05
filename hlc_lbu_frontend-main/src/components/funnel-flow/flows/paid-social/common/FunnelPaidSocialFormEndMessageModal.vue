<script setup lang="ts">
interface Props {
  imageSrc?: string;
  maxWidth?: string | number;
}

const props = withDefaults(defineProps<Props>(), {
  maxWidth: 500,
  imageSrc: "/images/celebrar-image.png",
});

const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <Modal
    v-model="isOpen"
    class="tw:p-10"
    :maxWidth="props.maxWidth"
    closeButton
  >
    <div
      v-if="!$slots.image && props.imageSrc"
      class="tw:mb-5 tw:flex tw:justify-center"
    >
      <img :src="props.imageSrc" alt="" />
    </div>

    <slot name="image" />

    <h3
      v-if="$slots.title"
      class="tw:mb-5 tw:text-center tw:text-xl tw:font-bold"
    >
      <slot name="title" />
    </h3>

    <p v-if="$slots.description" class="tw:mb-5 tw:text-center">
      <slot name="description" />
    </p>

    <div
      v-if="$slots.actions"
      class="tw:flex tw:flex-col tw:items-center tw:gap-3"
    >
      <slot name="actions" />
    </div>
  </Modal>
</template>
