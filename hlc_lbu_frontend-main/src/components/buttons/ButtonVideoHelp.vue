<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

const props = defineProps<{ src?: string }>();

// Modal state
const isModalOpen = ref(false);

// Handle help button click
const handleHelpButtonClick = () => {
  if (props.src) {
    isModalOpen.value = true;
  }
};
</script>

<template>
  <HelpButton @click="handleHelpButtonClick" />

  <!-- YouTube Video Modal -->
  <ModalVideoPlayer
    v-if="src && isModalOpen"
    v-model="isModalOpen"
    :src="src"
    v-bind="$attrs"
  >
    <template #title>
      <slot />
    </template>
  </ModalVideoPlayer>
</template>
