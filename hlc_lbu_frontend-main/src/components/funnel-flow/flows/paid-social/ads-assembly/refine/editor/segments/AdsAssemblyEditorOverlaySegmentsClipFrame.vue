<script setup lang="ts">
import { VideoSegment } from "@/services/funnel-flow/paid-social/VideoApi";

const props = defineProps<{
  /** Shows a placeholder while missing. */
  clip?: VideoSegment;
  /** A player. Without them it's a thumbnail of the clip's first frame. */
  controls?: boolean;
}>();

const { src, refresh } = useStoredFileSrc(() => ({
  storage_key: props.clip?.storage_key,
  storage_url: props.clip?.storage_path,
}));

// A thumbnail isn't played, so the start time makes the browser load a frame
// to show instead of a black box
const videoSrc = computed(() =>
  src.value && !props.controls ? `${src.value}#t=0.1` : src.value,
);
</script>

<!-- A 9:16 clip. Its width is set by the parent -->
<template>
  <div
    class="tw:flex tw:aspect-[9/16] tw:items-center tw:justify-center tw:overflow-hidden tw:rounded-md tw:bg-gray-100"
  >
    <video
      v-if="videoSrc"
      :key="videoSrc"
      :src="videoSrc"
      class="tw:h-full tw:w-full tw:bg-black tw:object-contain"
      :class="{ 'tw:pointer-events-none': !controls }"
      :controls="controls"
      :muted="!controls"
      playsinline
      preload="metadata"
      @error="refresh"
    />

    <Icon
      v-else
      icon="tabler:video"
      class="tw:text-[48px] tw:text-gray-500"
      aria-hidden="true"
    />
  </div>
</template>
