<script lang="ts" setup>
import { VTextarea } from "vuetify/components";
import { FieldInputTextBasicProps } from "./common-field-props";

export interface FieldBaseTextareaProps extends FieldInputTextBasicProps {
  rows?: number;
  maxCharacters?: number;
  characterCounter?: boolean;
  characterCounterPosition?: "start" | "end";

  maxVisibleLines?: number;
  warningLimit?: number;
}

const props = withDefaults(defineProps<FieldBaseTextareaProps>(), {
  orientation: "vertical",
  rows: 3,
  characterCounterPosition: "start",
});

const model = defineModel<string | number | undefined>({ required: true });
const emit = defineEmits<{
  focus: [e: Event];
  blur: [e: Event];
  change: [e: Event];
  clickLeftIcon: [e: MouseEvent];
  clickRightIcon: [e: MouseEvent];
}>();

const handleFocus = (e: Event) => {
  emit("focus", e);
};

const handleBlur = (e: Event) => {
  emit("change", e);
  emit("blur", e);
};

const onSpeechRecognitionTextReady = (text: string) => {
  model.value = (model.value ? `${model.value} ` : "") + text;
};

const textareaFieldRef = ref<InstanceType<typeof VTextarea>>();

defineExpose({
  focus: (options?: FocusOptions | undefined) =>
    textareaFieldRef.value?.focus(options),
  blur: () => textareaFieldRef.value?.blur(),
});

const displayAsError = computed(() => {
  if (props.error) return true;

  if (
    typeof model.value === "string" &&
    props.warningLimit &&
    model.value.length > props.warningLimit
  ) {
    return true;
  }

  return false;
});

//#region Character counter messages
const isWarning = computed(() => {
  if (
    typeof model.value !== "string" ||
    !props.maxCharacters ||
    !props.warningLimit
  ) {
    return false;
  }

  return (
    model.value.length > props.maxCharacters &&
    model.value.length <= props.warningLimit
  );
});

const isSuccess = computed(() => {
  if (typeof model.value !== "string" || !props.maxCharacters) {
    return false;
  }

  return model.value.length <= props.maxCharacters;
});
//#endregion
</script>

<template>
  <FieldBaseControl
    :name="name"
    :label="label"
    :description="description"
    :required="required"
    :error="warningLimit ? undefined : error"
    :orientation="orientation"
    :hideLayout="hideLayout"
    :labelClass="labelClass"
  >
    <div class="tw:flex tw:items-start tw:gap-2 tw:md:gap-6">
      <!-- Variante autoGrow (comportamiento original) -->
      <VTextarea
        ref="textareaFieldRef"
        :id="name"
        :name="name"
        :placeholder="placeholder"
        v-model="model"
        :disabled="disabled"
        @focus="handleFocus"
        @blur="handleBlur"
        :error="displayAsError"
        class="custom-input"
        :class="props.inputClass"
        :autoGrow="maxVisibleLines ? false : true"
        :rows="maxVisibleLines ? maxVisibleLines : rows"
        :style="
          maxVisibleLines
            ? { overflowY: 'auto', resize: 'vertical' }
            : undefined
        "
        :loading="loading"
      >
        <template #prepend-inner v-if="$slots.left || leftIcon">
          <FieldIcon
            v-if="leftIcon"
            :icon="leftIcon"
            :iconClass="leftIconClass"
            :clickable="leftIconClickable"
            @click="emit('clickLeftIcon', $event)"
          />

          <slot name="left" />
        </template>

        <template
          #append-inner
          v-if="$slots.right || rightIcon || speechRecognition"
        >
          <FieldIcon
            v-if="rightIcon"
            :icon="rightIcon"
            :iconClass="rightIconClass"
            :clickable="rightIconClickable"
            @click="emit('clickRightIcon', $event)"
          />

          <SpeechRecognitionButton
            v-if="speechRecognition"
            @textReady="onSpeechRecognitionTextReady"
            :disabled="disabled"
            size="sm"
          />

          <slot name="right" />
        </template>
      </VTextarea>

      <slot name="buttons" />
    </div>

    <template v-if="warningLimit">
      <!-- Warning about character limit -->
      <div class="tw:mt-2 tw:flex tw:gap-2 tw:text-sm">
        <!-- Error -->
        <div v-if="displayAsError" class="tw:-mt-1.5">
          <FieldError v-if="error">
            {{ error }}
          </FieldError>
        </div>
        <!-- Warning -->
        <div v-else-if="isWarning" class="tw:text-warning">
          {{ $t("forms.tolerable-characters") }}
          <div class="tw:inline-block tw:cursor-pointer">
            <Tooltip>
              <Icon
                icon="tabler-info-circle"
                class="tw:-mb-1 tw:h-5 tw:w-5 tw:rounded-full tw:text-sm tw:text-warning"
              />
              <template #content>
                Text slightly long. It will be auto-scaled to fit.
              </template>
            </Tooltip>
          </div>
        </div>
        <!-- Success -->
        <div v-else-if="isSuccess" class="tw:inline-block tw:text-success">
          {{ $t("forms.acceptable-characters") }}
        </div>
        <!-- Counter -->
        <div
          v-if="model && String(model).length > 0"
          class="tw:inline-block tw:border-l tw:border-secondary/30 tw:pl-2"
          :class="{
            'tw:text-warning': isWarning,
            'tw:text-error': displayAsError,
            'tw:text-success': isSuccess,
            'tw:w-full tw:text-right': props.characterCounterPosition === 'end',
          }"
        >
          {{ typeof model === "string" ? model.length : 0 }}
          <span v-if="maxCharacters"> / {{ maxCharacters }}</span> Chars
          <div
            v-if="displayAsError"
            class="tw:ml-1 tw:inline-block tw:rounded-full tw:bg-error tw:px-2 tw:text-white"
          >
            Fix: {{ warningLimit && warningLimit - String(model).length }}
          </div>
        </div>
      </div>
    </template>
    <template v-else>
      <!-- Normal counter without warning -->
      <div
        v-if="characterCounter || maxCharacters"
        class="tw:text-sm"
        :class="{
          'tw:text-error': displayAsError,
          'tw:w-full tw:text-right': props.characterCounterPosition === 'end',
        }"
      >
        {{ typeof model === "string" ? model.length : 0 }}
        <span v-if="maxCharacters"> / {{ maxCharacters }}</span> characters
      </div>
    </template>

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
