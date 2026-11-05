<script setup lang="ts">
defineProps<{
  name: string;
  description: string;
  icon: string;
  disabled?: boolean;
}>();
</script>

<template>
  <CardBase
    is="button"
    class="tw:relative tw:w-full tw:p-5 tw:text-left"
    hover-color="primary"
    :disabled="disabled"
  >
    <CardTitle iconVariant="gray" :icon="icon">
      {{ name }}

      <template #subtitle>
        {{ description }}
      </template>
    </CardTitle>

    <Chip
      v-if="disabled"
      leftIcon="tabler-lock"
      class="tw:absolute tw:top-3 tw:right-3"
    >
      {{ $t("global.soon") }}
    </Chip>
  </CardBase>
</template>
