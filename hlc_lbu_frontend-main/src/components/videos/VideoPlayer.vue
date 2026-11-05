<script setup lang="ts">
defineProps<{ src?: string }>();
</script>

<template>
  <div class="tw:aspect-video tw:w-full">
    <YoutubeIframe
      v-if="src"
      :src="src"
      class="tw:h-full tw:w-full tw:rounded-lg"
    />

    <div
      v-else
      class="tw:flex tw:h-full tw:items-center tw:justify-center tw:rounded-[30px] tw:bg-black"
    >
      <Icon
        icon="tabler-player-play-filled"
        class="tw:text-[154px] tw:text-white"
      />
    </div>
  </div>
</template>
