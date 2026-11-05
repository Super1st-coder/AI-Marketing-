<script lang="ts" setup>
defineProps<{ setVoice?: boolean }>();
</script>

<template>
  <Chip v-if="setVoice" color="success" leftIcon="tabler-microphone">
    {{ $t("brands.voice-added") }}
  </Chip>
  <Chip v-else leftIcon="tabler-microphone-off">
    {{ $t("brands.not-voice-added") }}
  </Chip>
</template>
