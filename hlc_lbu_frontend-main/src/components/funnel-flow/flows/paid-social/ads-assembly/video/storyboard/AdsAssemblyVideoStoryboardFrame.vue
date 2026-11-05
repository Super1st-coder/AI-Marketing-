<script setup lang="ts">
import { StoryboardShotImage } from "./storyboardShotImages";

const props = withDefaults(
  defineProps<{
    /** Shows a placeholder while missing. */
    image?: StoryboardShotImage;
    alt?: string;
  }>(),
  {
    alt: "",
  },
);

const { src, refresh } = useStoredFileSrc(() => ({
  storage_key: props.image?.storage_key,
  storage_url: props.image?.image_url,
}));
</script>

<!-- A 9:16 storyboard frame. Its width is set by the parent -->
<template>
  <div
    class="tw:flex tw:aspect-[9/16] tw:items-center tw:justify-center tw:overflow-hidden tw:rounded-md tw:bg-gray-100"
  >
    <img
      v-if="src"
      :key="src"
      :src="src"
      :alt="alt"
      class="tw:h-full tw:w-full tw:object-cover"
      @error="refresh"
    />

    <Icon
      v-else
      icon="tabler:photo"
      class="tw:text-[48px] tw:text-gray-500"
      aria-hidden="true"
    />
  </div>
</template>
