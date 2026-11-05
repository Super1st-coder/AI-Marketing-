<script lang="ts" setup>
export interface FieldBaseCheckboxProps {
  name?: string;
  label?: string;
  disabled?: boolean;
  size?: "md" | "lg";
  color?: "primary" | "success" | "error";
  variant?: "checkbox" | "switch";
  checked?: boolean;
}

const props = withDefaults(defineProps<FieldBaseCheckboxProps>(), {
  size: "md",
  color: "primary",
  variant: "checkbox",
  checked: undefined,
});

const internalModel = defineModel<boolean | undefined>();
const model = computed<boolean | undefined>({
  get: () => {
    if (props.checked !== undefined) {
      return props.checked;
    } else {
      return internalModel.value;
    }
  },
  set: (value) => {
    if (props.checked === undefined) {
      internalModel.value = value;
    }
  },
});
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
      type="checkbox"
      :id="name"
      :name="name"
      v-model="model"
      :disabled="disabled"
      v-bind="$attrs"
      hidden
    />

    <!-- Checkbox -->
    <span
      v-if="variant === 'checkbox'"
      class="tw:flex tw:cursor-pointer tw:items-center tw:justify-center tw:rounded tw:border-2 tw:text-white"
      :class="{
        'tw:h-[18px] tw:w-[18px]': size === 'md',
        'tw:h-6 tw:w-6': size === 'lg',

        'tw:border-gray-400': !model,
        'tw:border-primary tw:bg-primary': model && color === 'primary',
        'tw:border-success tw:bg-success': model && color === 'success',
        'tw:border-error tw:bg-error': model && color === 'error',
      }"
    >
      <Icon v-show="model" icon="tabler-check" width="100%" height="unset" />
    </span>

    <!-- Switch -->
    <span
      v-if="variant === 'switch'"
      class="tw:flex tw:cursor-pointer tw:rounded-full tw:p-0.5"
      :class="{
        'tw:h-[18px] tw:w-8': size === 'md',
        'tw:h-6 tw:w-10': size === 'lg',

        'tw:bg-gray-300': !model,
        'tw:justify-end': model,
        'tw:bg-primary': model && color === 'primary',
        'tw:bg-success': model && color === 'success',
        'tw:bg-error': model && color === 'error',
      }"
    >
      <span class="tw:aspect-square tw:rounded-full tw:bg-white"> </span>
    </span>

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
