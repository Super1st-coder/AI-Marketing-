<script lang="ts" setup>
import { FieldInputBasicProps } from "./common-field-props";
import { VTextField } from "vuetify/components";

/**
 * Date + time picker based on the native `<input type="datetime-local">`.
 * The value uses the native format, in the user's local time: `YYYY-MM-DDTHH:mm`.
 */
export interface FieldBaseDateTimeProps extends Omit<
  FieldInputBasicProps,
  "leftIcon" | "leftIconClass" | "leftIconClickable"
> {
  /** Earliest selectable value, in the `YYYY-MM-DDTHH:mm` format. */
  min?: string;
  /** Latest selectable value, in the `YYYY-MM-DDTHH:mm` format. */
  max?: string;
}

const props = withDefaults(defineProps<FieldBaseDateTimeProps>(), {
  orientation: "vertical",
});

const model = defineModel<string | undefined>({ required: true });

// The native input reports an empty string when cleared
const inputModel = computed({
  get: () => model.value ?? "",
  set: (value: string) => {
    model.value = value || undefined;
  },
});

const emit = defineEmits<{
  focus: [e: Event];
  blur: [e: Event];
  change: [e: Event];
  clickRightIcon: [e: MouseEvent];
}>();

const handleFocus = (e: Event) => {
  emit("focus", e);
};

const handleBlur = (e: Event) => {
  emit("change", e);
  emit("blur", e);
};

const textFieldRef = ref<InstanceType<typeof VTextField>>();

function getInputElement() {
  return (textFieldRef.value?.$el as HTMLElement | undefined)?.querySelector(
    "input",
  );
}

// The native picker indicator is hidden, so clicking anywhere on the field opens it
function openPicker() {
  const input = getInputElement();

  if (!input || props.disabled) {
    return;
  }

  try {
    input.showPicker();
  } catch (error) {
    console.error("Failed to open the date time picker:", error);
    input.focus();
  }
}

defineExpose({
  focus: (options?: FocusOptions | undefined) =>
    textFieldRef.value?.focus(options),
  blur: () => textFieldRef.value?.blur(),
  openPicker,
});
</script>

<template>
  <FieldBaseControl
    :name="name"
    :label="label"
    :description="description"
    :required="required"
    :optional="optional"
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
        :placeholder="placeholder"
        type="datetime-local"
        :min="min"
        :max="max"
        v-model="inputModel"
        :disabled="disabled"
        @focus="handleFocus"
        @blur="handleBlur"
        @click:control="openPicker"
        :error="!!error"
        class="custom-input tw:[&_input::-webkit-calendar-picker-indicator]:hidden"
        :class="props.inputClass"
        :loading="loading"
      >
        <template #prepend-inner>
          <FieldIcon icon="tabler:calendar" />

          <slot name="left" />
        </template>

        <template #append-inner v-if="$slots.right || rightIcon">
          <FieldIcon
            v-if="rightIcon"
            :icon="rightIcon"
            :iconClass="rightIconClass"
            :clickable="rightIconClickable"
            @click.stop="emit('clickRightIcon', $event)"
          />

          <slot name="right" />
        </template>
      </VTextField>
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
