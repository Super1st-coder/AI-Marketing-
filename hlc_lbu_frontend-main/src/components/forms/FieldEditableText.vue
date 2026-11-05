<script lang="ts" setup>
import { useField } from "vee-validate";

interface Props {
  name: string;
  required?: boolean;
  inputClass?: string;
  type?: "text" | "textarea";
  variant?: "default" | "text";
  color?: "normal" | "dark";
  placeholder?: string;
  disabled?: boolean;
  fit?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  type: "textarea",
  required: true,
  fit: true,
});

const { value: model, errorMessage } = useField<string>(() => props.name);
</script>

<template>
  <FieldBaseEditableText
    v-model="model"
    :required="required"
    :type="type"
    :variant="variant"
    :color="color"
    :fit="fit"
    preventScroll
    :inputClass="inputClass"
    :placeholder="placeholder"
    :disabled="disabled"
    :error="errorMessage"
  />
</template>
