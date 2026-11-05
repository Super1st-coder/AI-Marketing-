<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldBaseSelectProps } from "./FieldBaseSelect.vue";

interface Props extends FieldBaseSelectProps {
  name: string;
}

const props = defineProps<Props>();

const {
  value: model,
  errorMessage,
  handleChange: _handleChange,
  handleBlur: _handleBlur,
} = useField(() => props.name, undefined);

const handleChange = (e: Event) => {
  _handleChange(e);
};

const handleBlur = (e: Event) => {
  _handleBlur(e);
};
</script>

<template>
  <FieldBaseSelect
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
  </FieldBaseSelect>
</template>
