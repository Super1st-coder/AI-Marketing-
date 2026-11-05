<script setup lang="ts">
// A video thumbnail that plays and pauses on click, like `ImgFile` for images:
// it takes a picked file or a link

const props = defineProps<{
  src?: File | Blob | string | null;
  /** Read by screen readers, since the button has no text. */
  label: string;
}>();

const emit = defineEmits<{
  /** The video couldn't be loaded or played, e.g. its link expired. */
  error: [];
}>();

const fileUrl = useObjectUrl(() =>
  props.src instanceof Blob ? props.src : undefined,
);
const src = computed(() =>
  typeof props.src === "string" ? props.src : fileUrl.value,
);

const videoRef = useTemplateRef("videoRef");
const isPlaying = ref(false);

function handleTogglePlay() {
  const video = videoRef.value;
  if (!video) return;

  if (video.paused) {
    video.play().catch((error) => {
      console.error("Failed to play the video:", error);
    });
  } else {
    video.pause();
  }
}
</script>

<template>
  <button
    type="button"
    class="tw:relative tw:rounded-lg tw:bg-gray-900"
    :disabled="!src"
    :aria-label="label"
    @click="handleTogglePlay"
  >
    <div class="tw:h-full tw:w-full tw:overflow-hidden tw:rounded-[inherit]">
      <video
        v-if="src"
        ref="videoRef"
        :src="src"
        class="tw:h-full tw:w-full tw:object-cover"
        playsinline
        preload="metadata"
        @play="isPlaying = true"
        @pause="isPlaying = false"
        @ended="isPlaying = false"
        @error="
          isPlaying = false;
          emit('error');
        "
      />
    </div>

    <Icon
      v-if="!isPlaying"
      icon="tabler:player-play-filled"
      class="tw:absolute tw:inset-0 tw:m-auto tw:text-[24px] tw:text-white"
      aria-hidden="true"
    />

    <slot />
  </button>
</template>
