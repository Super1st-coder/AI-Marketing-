<script lang="ts" setup>
defineProps<{
  closable?: boolean;
}>();
</script>

<template>
  <Chip variant="label" color="primary" class="tw:group">
    <slot />

    <button
      v-if="closable"
      type="button"
      class="tw:ml-1 tw:flex tw:items-center tw:justify-center tw:rounded tw:hover:bg-black/10"
      :aria-label="$t('global.remove')"
    >
      <Icon icon="tabler-x" class="tw:text-base" />
    </button>
  </Chip>
</template>
