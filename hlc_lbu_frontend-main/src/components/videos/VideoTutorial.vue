<script setup lang="ts">
defineProps<{ videoSrc?: string }>();
</script>

<template>
  <div
    class="tw:mx-auto tw:flex tw:h-full tw:w-full tw:max-w-[800px] tw:flex-col tw:items-center tw:justify-center tw:text-center"
  >
    <Chip
      v-if="$slots.chip"
      size="md"
      color="primary"
      variant="label"
      class="tw:mb-4"
    >
      <slot name="chip" />
    </Chip>

    <PageTitle v-if="$slots.title" class="tw:mb-3" size="lg">
      <slot name="title" />
    </PageTitle>

    <p v-if="$slots.description" class="tw:mb-10 tw:text-sm tw:text-gray-500">
      <slot name="description" />
    </p>

    <div class="tw:mb-10 tw:w-full">
      <VideoPlayer :src="videoSrc" />
    </div>

    <p
      v-if="$slots.actionsDescription"
      class="tw:mb-3 tw:text-sm tw:text-gray-500"
    >
      <slot name="actionsDescription" />
    </p>

    <div
      v-if="$slots.actions"
      class="tw:flex tw:flex-col tw:justify-center tw:gap-6"
    >
      <slot name="actions" />
    </div>
  </div>
</template>
