<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldBaseNewSelectProps } from "./FieldBaseNewSelect.vue";

interface Props extends FieldBaseNewSelectProps {
  name: string;
}

const props = defineProps<Props>();

const {
  value: model,
  errorMessage,
  handleChange: _handleChange,
  handleBlur: _handleBlur,
} = useField(() => props.name, undefined);

const handleBlur = (e: Event) => {
  _handleBlur(e);
};
</script>

<template>
  <FieldBaseNewSelect
    v-bind="props"
    v-model="model"
    @blur="handleBlur"
    :error="errorMessage"
  >
    <!-- Pass all the slots -->
    <template v-for="(_, name) in $slots" #[name]="scope">
      <slot :name v-bind="scope ?? {}" />
    </template>
  </FieldBaseNewSelect>
</template>
