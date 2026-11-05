<script lang="ts" setup>
import { VSlider } from "vuetify/components";
import { FieldBasicProps, FieldLayoutProps } from "./common-field-props";

export interface FieldBaseSliderProps
  extends FieldBasicProps, FieldLayoutProps {
  min: number;
  max: number;
  step?: number;
  format?: (value: number) => string;
  alwaysShowThumbLabel?: boolean;
}

const props = withDefaults(defineProps<FieldBaseSliderProps>(), {
  orientation: "vertical",
  step: 1,
});

const model = defineModel<number>({ required: true });
const emit = defineEmits<{
  focus: [e: Event];
  blur: [e: Event];
  change: [value: number];
}>();

const handleFocus = (e: Event) => {
  emit("focus", e);
};

const handleBlur = (e: Event) => {
  emit("blur", e);
};

const formatValue = (value: number) =>
  props.format ? props.format(value) : String(value);
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
    <div>
      <VSlider
        :id="name"
        :name="name"
        v-model="model"
        :min="min"
        :max="max"
        :step="step"
        :disabled="disabled"
        :thumb-label="alwaysShowThumbLabel ? 'always' : undefined"
        hide-details
        @focus="handleFocus"
        @blur="handleBlur"
        @update:modelValue="emit('change', $event)"
      >
        <template #thumb-label="{ modelValue }">
          {{ formatValue(modelValue) }}
        </template>
      </VSlider>

      <div class="tw:flex tw:justify-between tw:text-sm tw:text-secondary-text">
        <span>{{ formatValue(min) }}</span>
        <span>{{ formatValue(max) }}</span>
      </div>
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

<style scoped>
:deep(.v-slider-thumb__label) {
  white-space: nowrap;
}
</style>
