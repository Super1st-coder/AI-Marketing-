<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldBaseTextareaProps } from "./FieldBaseTextarea.vue";

interface Props extends FieldBaseTextareaProps {
  name: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  blur: [e: Event];
}>();

const {
  value: model,
  errorMessage,
  handleChange: _handleChange,
  handleBlur: _handleBlur,
} = useField<string | number | undefined>(() => props.name, undefined);

const handleChange = (e: Event) => {
  _handleChange(e);
};

const handleBlur = (e: Event) => {
  _handleBlur(e);
  emit("blur", e);
};
</script>

<template>
  <FieldBaseTextarea
    v-bind="props"
    v-model="model"
    @change="handleChange"
    @blur="handleBlur"
    :error="errorMessage"
  >
    <!-- Pass all the slots -->
    <template v-for="(_, name) in $slots" #[name]="scope">
      <slot :name v-bind="scope ?? {}" />
    </template>
  </FieldBaseTextarea>
</template>
