<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldBaseDateTimeProps } from "./FieldBaseDateTime.vue";

interface Props extends FieldBaseDateTimeProps {
  name: string;
}

const props = defineProps<Props>();

const {
  value: model,
  errorMessage,
  handleChange: _handleChange,
  handleBlur: _handleBlur,
} = useField<string | undefined>(() => props.name, undefined);

// Validate with the model value, so a cleared input stays `undefined`
// instead of the native empty string
const handleChange = () => {
  _handleChange(model.value);
};

const handleBlur = (e: Event) => {
  _handleBlur(e);
};
</script>

<template>
  <FieldBaseDateTime
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
  </FieldBaseDateTime>
</template>
