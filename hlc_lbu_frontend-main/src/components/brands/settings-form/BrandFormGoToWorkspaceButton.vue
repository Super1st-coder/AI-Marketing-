<script setup lang="ts">
const store = useBrandFormStore();
</script>

<template>
  <Tooltip :disabled="store.isCompleted" placement="top" :maxWidth="231">
    <Button
      variant="outlined"
      color="primary"
      leftIcon="tabler:device-desktop"
      :to="{ name: 'Brand' }"
      :disabled="!store.isCompleted"
      :uppercase="false"
    >
      {{ $t("brands.settings.workspace-button.label") }}
    </Button>

    <template #content>
      {{ $t("brands.settings.workspace-button.tooltip") }}
    </template>
  </Tooltip>
</template>
