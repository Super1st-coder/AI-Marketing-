<script lang="ts" setup generic="T">
export interface FieldBaseRadioProps<T> {
  name: string;
  value: T;
  label?: string;
  disabled?: boolean;
  size?: "md" | "lg";
  color?: "primary" | "success" | "error";
}

const props = withDefaults(defineProps<FieldBaseRadioProps<T>>(), {
  size: "md",
  color: "primary",
  variant: "checkbox",
});

const model = defineModel<T | undefined>();

const isSelected = computed(() => model.value === props.value);
</script>

<template>
  <label
    :for="name"
    class="tw:flex tw:items-center tw:gap-2"
    :class="{
      'tw:cursor-pointer': !disabled,
    }"
  >
    <!-- Hidden input -->
    <input
      type="radio"
      :id="name"
      :name="name"
      :value="value"
      v-model="model"
      :disabled="disabled"
      v-bind="$attrs"
      hidden
    />

    <!-- Radio -->
    <span
      class="tw:flex tw:cursor-pointer tw:items-center tw:justify-center tw:rounded-full tw:border-2 tw:bg-white tw:text-white"
      :class="{
        'tw:h-[18px] tw:w-[18px]': size === 'md',
        'tw:h-6 tw:w-6': size === 'lg',

        'tw:border-gray-400': !isSelected,
        'tw:border-[6px]': isSelected,
        'tw:border-primary': isSelected && color === 'primary',
        'tw:border-success': isSelected && color === 'success',
        'tw:border-error': isSelected && color === 'error',

        'tw:pointer-events-auto': !disabled,
        'tw:pointer-events-none tw:opacity-50': disabled,
      }"
    />

    <!-- Label -->
    <span
      v-if="label || $slots.label"
      class="tw:font-semibold tw:text-gray-700"
    >
      {{ label }}
      <slot name="label" />
    </span>
  </label>
</template>
