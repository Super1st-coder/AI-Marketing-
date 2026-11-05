<script lang="ts" setup>
defineProps<{ completed?: boolean }>();
</script>

<template>
  <Chip v-if="completed" color="success" variant="label">
    {{ $t("global.ready-to-use") }}
  </Chip>
  <Chip v-else color="error" variant="label">
    {{ $t("global.incomplete") }}
  </Chip>
</template>
