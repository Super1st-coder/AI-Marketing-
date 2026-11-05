<script lang="ts" setup>
import { InputTypeHTMLAttribute } from "vue";
import { FieldInputTextBasicProps } from "./common-field-props";
import { VTextField } from "vuetify/components";

export interface FieldBaseTextProps extends FieldInputTextBasicProps {
  type?: InputTypeHTMLAttribute;
}

const props = withDefaults(defineProps<FieldBaseTextProps>(), {
  orientation: "vertical",
  type: "text",
});

const isActive = ref(false);

const model = defineModel<string | undefined>({ required: true });
const emit = defineEmits<{
  focus: [e: Event];
  blur: [e: Event];
  change: [e: Event];
  clickLeftIcon: [e: MouseEvent];
  clickRightIcon: [e: MouseEvent];
}>();

const handleFocus = (e: Event) => {
  emit("focus", e);
  isActive.value = true;
};

const handleBlur = (e: Event) => {
  emit("change", e);
  emit("blur", e);
  isActive.value = false;
};

const onSpeechRecognitionTextReady = (text: string) => {
  model.value = (model.value ? `${model.value} ` : "") + text;
};

const textFieldRef = ref<InstanceType<typeof VTextField>>();

defineExpose({
  focus: (options?: FocusOptions | undefined) =>
    textFieldRef.value?.focus(options),
  blur: () => textFieldRef.value?.blur(),
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
        :placeholder="placeholder"
        :type="type"
        v-model="model"
        :disabled="disabled"
        @focus="handleFocus"
        @blur="handleBlur"
        :error="!!error"
        class="custom-input"
        :class="props.inputClass"
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
