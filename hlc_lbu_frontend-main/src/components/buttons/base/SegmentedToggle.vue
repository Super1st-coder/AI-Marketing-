<script setup lang="ts">
interface SegmentedToggleOption {
  value: string;
  label: string;
}

defineProps<{ options: SegmentedToggleOption[] }>();

const model = defineModel<string>({ required: true });
</script>

<template>
  <div
    class="tw:flex tw:w-full tw:gap-1 tw:rounded-xl tw:border-2 tw:border-gray-200 tw:bg-[#F7F5F3] tw:p-1"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="tw:flex-1 tw:rounded-lg tw:border tw:px-4 tw:py-2.5 tw:text-sm tw:font-medium"
      :class="
        model === option.value
          ? 'tw:border-gray-300 tw:bg-white tw:text-primary-text tw:shadow-[0_1px_2px] tw:shadow-[#101828]/10'
          : 'tw:border-transparent tw:text-gray-500'
      "
      @click="model = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>
