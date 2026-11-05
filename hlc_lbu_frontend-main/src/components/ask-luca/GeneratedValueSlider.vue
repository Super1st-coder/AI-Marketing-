<script setup lang="ts">
defineProps<{
  currentIndex?: number;
  itemCount?: number;
  disabled?: boolean;
}>();

const emit = defineEmits<{ move: [number] }>();
</script>

<template>
  <div
    v-if="itemCount && itemCount > 0 && currentIndex !== undefined"
    class="tw:flex tw:items-center tw:gap-2.5"
    :class="{ 'tw:opacity-45': disabled }"
  >
    <span v-if="$slots.default" class="tw:text-sm">
      <slot />
    </span>

    <div
      class="tw:flex tw:items-center tw:rounded-lg tw:border tw:border-gray-300 tw:bg-white tw:text-sm tw:text-gray-600"
    >
      <button
        class="tw:px-3 tw:py-2"
        type="button"
        @click="emit('move', -1)"
        :disabled="disabled"
      >
        <Icon icon="tabler:arrow-left" />
      </button>

      <span class="tw:text-xs tw:font-medium">
        {{
          $t("global.current-of-total", {
            current: currentIndex + 1,
            total: itemCount,
          })
        }}
      </span>

      <button
        class="tw:px-3 tw:py-2"
        type="button"
        @click="emit('move', 1)"
        :disabled="disabled"
      >
        <Icon icon="tabler:arrow-right" />
      </button>
    </div>
  </div>
</template>
