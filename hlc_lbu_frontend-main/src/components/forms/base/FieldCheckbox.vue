<script lang="ts" setup>
import { useField } from "vee-validate";
import { type FieldBaseCheckboxProps } from "./FieldBaseCheckbox.vue";

interface Props extends FieldBaseCheckboxProps {
  name: string;
}

const props = withDefaults(defineProps<Props>(), {
  checked: undefined,
});

const { value: model, errorMessage } = useField<boolean | undefined>(
  () => props.name,
  undefined,
);
</script>

<template>
  <FieldBaseCheckbox v-bind="props" v-model="model" :error="errorMessage" />
</template>
