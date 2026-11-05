<script setup lang="ts">
// A video the user uploaded, or picked and hasn't saved yet
defineProps<{
  name: string;
  /** In bytes. Unknown for files saved before it was kept. */
  size?: number;
  /** Plays the video in the thumbnail. */
  src?: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  remove: [];
  /** The video couldn't be loaded or played, e.g. its link expired. */
  error: [];
}>();
</script>

<template>
  <div
    class="tw:flex tw:items-center tw:gap-4 tw:rounded-xl tw:bg-gray-100 tw:p-4"
  >
    <VideoFilePlayButton
      :src="src"
      :label="$t('forms.file-upload.play-video', { name })"
      class="tw:h-11 tw:w-16 tw:shrink-0"
      @error="emit('error')"
    >
      <Icon
        icon="tabler:circle-check-filled"
        class="tw:absolute tw:-right-1.5 tw:-bottom-1.5 tw:rounded-full tw:bg-white tw:text-lg tw:text-success"
        aria-hidden="true"
      />
    </VideoFilePlayButton>

    <div class="tw:min-w-0 tw:grow">
      <p class="tw:truncate tw:font-medium" :title="name">{{ name }}</p>

      <p v-if="size !== undefined" class="tw:text-sm tw:text-secondary-text">
        {{ formatFileSize(size) }}
      </p>
    </div>

    <button
      type="button"
      class="tw:flex tw:shrink-0 tw:text-2xl tw:disabled:opacity-50"
      :disabled="disabled"
      :aria-label="$t('forms.file-upload.remove-file', { name })"
      @click="emit('remove')"
    >
      <Icon icon="tabler:x" aria-hidden="true" />
    </button>
  </div>
</template>
