<script setup lang="ts">
// Props y v-model
const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  label: {
    type: String,
    default: "",
  },
  disabled: {
    type: Boolean,
    required: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

const isChecked = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});
</script>

<template>
  <div
    class="tw:flex tw:items-center tw:gap-4"
    :class="{
      'tw:cursor-default': disabled,
      'tw:cursor-pointer': !disabled,
    }"
  >
    <input
      type="checkbox"
      v-model="isChecked"
      :disabled="disabled"
      class="tw:hidden"
    />

    <span
      class="tw:border-secondary-400 tw:flex tw:h-4 tw:w-4 tw:items-center tw:justify-center tw:rounded tw:border"
      :class="{
        'tw:border-primary tw:bg-primary': isChecked,
      }"
    >
      <Icon
        v-if="isChecked"
        icon="tabler-check"
        class="tw:text-xl tw:text-white"
      />
    </span>

    <span
      class="tw:text-secondary-700 tw:text-base tw:font-medium"
      :class="{ 'tw:text-primary-600': isChecked }"
    >
      {{ label }}
    </span>
  </div>
</template>
