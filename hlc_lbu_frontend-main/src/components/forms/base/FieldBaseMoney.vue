<script lang="ts" setup>
import { FieldInputBasicProps } from "./common-field-props";
import { VTextField } from "vuetify/components";
import { vMaska } from "maska/vue";
import type { MaskInputOptions } from "maska";

export interface FieldBaseMoneyProps extends FieldInputBasicProps {
  currency?: string;
  appendCodeToLabel?: boolean;
  useCurrencyIcon?: boolean;
}

const props = withDefaults(defineProps<FieldBaseMoneyProps>(), {
  orientation: "vertical",
  currency: undefined,
  appendCodeToLabel: false,
  useCurrencyIcon: false,
});

const isActive = ref(false);

const locale = computed(() => DEFAULT_NUMBER_LOCALE);
const currencyInfo = computed(() => getCurrencyInfo(props.currency));
const code = computed(() => currencyInfo.value.code);
const digits = computed(() => currencyInfo.value.digits);
const currencyIcon = computed(() => currencyInfo.value.icon);

// Actual value shared with the outside world
const model = defineModel<number | undefined>({ required: true });

// Initial values for the Maska refs, we need this because of a bug: https://stackoverflow.com/a/78771313
const initialMaskedValue =
  typeof model.value === "number"
    ? new Intl.NumberFormat(locale.value).format(model.value)
    : undefined;
const initialUnmaskedValueValue = model.value;

// Refs to use with Maska
const maskedValue = ref<string | undefined>(initialMaskedValue);
const unmaskedValue = ref<string | undefined>(
  initialUnmaskedValueValue?.toString(),
);

// Placeholder
const defaultPlaceholder = computed(() =>
  new Intl.NumberFormat(locale.value, {
    minimumFractionDigits: digits.value,
  }).format(0),
);

// Keep model synced with unmaskedValue
watch(unmaskedValue, (unmaskedValue) => {
  if (unmaskedValue !== undefined && unmaskedValue !== "") {
    model.value = parseFloat(unmaskedValue);
  } else {
    model.value = undefined;
  }
});

// Keep unmaskedValue / maskedValue synced with model (e.g. setFieldValue)
watch(model, (modelValue) => {
  if (modelValue !== undefined) {
    const nextUnmasked = modelValue.toString();
    const nextMasked = new Intl.NumberFormat(locale.value).format(modelValue);

    if (unmaskedValue.value !== nextUnmasked) {
      unmaskedValue.value = nextUnmasked;
    }

    if (maskedValue.value !== nextMasked) {
      maskedValue.value = nextMasked;
    }
  } else {
    unmaskedValue.value = "";
    maskedValue.value = undefined;
  }
});

const emit = defineEmits<{
  focus: [e: Event | unknown];
  change: [e: Event | unknown];
  clickLeftIcon: [e: MouseEvent];
  clickRightIcon: [e: MouseEvent];
}>();

const handleFocus = (_e: Event) => {
  emit("focus", model.value);
  isActive.value = true;
};

const handleBlur = (_e: Event) => {
  emit("change", model.value);
  isActive.value = false;
};

const options = computed<MaskInputOptions>(() => ({
  number: {
    locale: locale.value,
    fraction: digits.value,
    unsigned: true,
  },
}));

const textFieldRef = ref<InstanceType<typeof VTextField>>();

defineExpose({
  focus: (options?: FocusOptions | undefined) =>
    textFieldRef.value?.focus(options),
  blur: () => textFieldRef.value?.blur(),
  unmaskedValue,
});
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
      <VTextField
        ref="textFieldRef"
        :id="name"
        :name="name"
        :placeholder="placeholder ?? defaultPlaceholder"
        type="text"
        v-model="maskedValue"
        v-maska:unmaskedValue.unmasked="options"
        :disabled="disabled"
        @focus="handleFocus"
        @blur="handleBlur"
        :error="!!error"
        class="custom-input"
        :class="props.inputClass"
        :loading="loading"
      >
        <template
          #prepend-inner
          v-if="$slots.left || leftIcon || (useCurrencyIcon && currencyIcon)"
        >
          <FieldIcon
            v-if="leftIcon || (useCurrencyIcon && currencyIcon)"
            :icon="leftIcon ?? currencyIcon"
            :iconClass="leftIconClass"
            :clickable="leftIconClickable"
            @click="emit('clickLeftIcon', $event)"
          />

          <slot name="left" />
        </template>

        <template #append-inner v-if="$slots.right || rightIcon">
          <FieldIcon
            v-if="rightIcon"
            :icon="rightIcon"
            :iconClass="rightIconClass"
            :clickable="rightIconClickable"
            @click="emit('clickRightIcon', $event)"
          />

          <slot name="right" />
        </template>
      </VTextField>
    </div>

    <template v-if="$slots.label" #label>
      <slot name="label" />
    </template>
    <template v-else-if="appendCodeToLabel" #label>
      {{ label }} ({{ code }})
    </template>
    <template v-if="$slots.labelHelp" #labelHelp>
      <slot name="labelHelp" />
    </template>
    <template v-if="$slots.hint" #hint>
      <slot name="hint" />
    </template>
  </FieldBaseControl>
</template>
