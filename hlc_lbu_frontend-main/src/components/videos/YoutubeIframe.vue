<script setup lang="ts">
const props = defineProps<{ src?: string }>();

// Extract YouTube video ID from URL
const getYouTubeVideoId = (url: string) => {
  const regex =
    /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
  const match = url.match(regex);

  return match ? match[1] : undefined;
};

const videoId = computed(() =>
  props.src ? getYouTubeVideoId(props.src) : undefined,
);
</script>

<template>
  <iframe
    v-if="src"
    :src="`https://www.youtube.com/embed/${videoId}`"
    title="YouTube video player"
    frameborder="0"
    allow="
      accelerometer;
      autoplay;
      clipboard-write;
      encrypted-media;
      gyroscope;
      picture-in-picture;
      web-share;
    "
    referrerpolicy="strict-origin-when-cross-origin"
    allowfullscreen
  ></iframe>
</template>
