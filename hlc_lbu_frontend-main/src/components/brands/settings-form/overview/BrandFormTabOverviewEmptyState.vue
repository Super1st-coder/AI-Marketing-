<script setup lang="ts">
const emit = defineEmits<{
  add: [];
}>();
</script>

<template>
  <div class="tw:flex tw:flex-col tw:items-center tw:gap-5 tw:py-6">
    <p class="tw:text-gray-500">
      <slot />
    </p>

    <Button
      variant="outlined"
      color="secondary"
      left-icon="tabler-plus"
      size="sm"
      type="button"
      @click="emit('add')"
    >
      {{ $t("brands.settings.overview.add-button") }}
    </Button>
  </div>
</template>
