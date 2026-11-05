<script lang="ts" setup>
import { FieldInputBasicProps } from "./common-field-props";

export type SelectOption = { value: unknown; label: string };

export interface FieldBaseSelectProps extends FieldInputBasicProps {
  options: SelectOption[];
  orientation?: "horizontal" | "vertical";
}

const props = withDefaults(defineProps<FieldBaseSelectProps>(), {
  orientation: "vertical",
});

const model = defineModel<unknown>({ required: true });
const emit = defineEmits<{
  focus: [e: Event];
  blur: [e: Event];
  change: [e: Event];
}>();

const handleFocus = (e: Event) => {
  emit("focus", e);
};

const handleChange = (e: Event) => {
  emit("change", e);
};

const handleBlur = (e: Event) => {
  emit("change", e);
};

const isEmpty = computed(
  () => model.value === undefined || model.value === null,
);
</script>

<template>
  <FieldBaseControl
    :name="name"
    :label="label"
    :description="description"
    :required="required"
    :error="error"
    :orientation="orientation"
    :hideLayout="hideLayout"
    :labelClass="labelClass"
  >
    <div class="tw:flex tw:items-start tw:gap-2 tw:md:gap-6">
      <select
        :id="name"
        :name="name"
        v-model="model"
        @focus="handleFocus"
        @change="handleChange"
        @blur="handleBlur"
        class="tw:w-full tw:appearance-auto tw:rounded-xl tw:border tw:border-gray-300 tw:px-4 tw:py-2.5 tw:font-medium tw:shadow-[0_1px_2px] tw:shadow-gray-900/5 tw:outline-hidden"
        :class="[
          props.inputClass,
          {
            'tw:bg-white': !disabled,
            'tw:text-gray-400': !disabled && isEmpty,
            'tw:text-gray-700': !disabled && !isEmpty,
            'tw:bg-gray-100 tw:text-gray-400': disabled,
          },
        ]"
        :disabled="disabled"
      >
        <option :value="undefined" disabled selected hidden>
          {{ placeholder }}
        </option>

        <option
          v-if="!options.find((option) => option.value === '')"
          :value="''"
          disabled
          selected
          hidden
        >
          {{ placeholder }}
        </option>

        <option
          v-if="!options.find((option) => option.value === null)"
          :value="null"
          disabled
          selected
          hidden
        >
          {{ placeholder }}
        </option>

        <option
          v-if="!options.find((option) => option.value === -1)"
          :value="-1"
          disabled
          selected
          hidden
        >
          {{ placeholder }}
        </option>

        <option
          v-for="option in options"
          :key="option.label"
          :value="option.value"
          class="tw:text-gray-700"
        >
          {{ option.label }}
        </option>
      </select>
    </div>

    <template v-if="$slots.label" #label>
      <slot name="label" />
    </template>
    <template v-if="$slots.labelHelp" #labelHelp>
      <slot name="labelHelp" />
    </template>
    <template v-if="$slots.hint" #hint>
      <slot name="hint" />
    </template>
  </FieldBaseControl>
</template>
