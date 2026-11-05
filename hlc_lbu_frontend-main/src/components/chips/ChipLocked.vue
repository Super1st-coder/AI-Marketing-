<script lang="ts" setup>
defineProps<{ locked?: boolean }>();
const { t } = useI18n();
</script>

<template>
  <Chip v-if="locked" color="secondary" variant="label" leftIcon="tabler-lock">
    {{ t("global.locked") }}
  </Chip>
</template>
