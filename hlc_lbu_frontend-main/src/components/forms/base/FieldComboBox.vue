<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldComboBoxProps } from "./FieldBaseComboBox.vue";

interface Props extends FieldComboBoxProps {
  name: string;
  label: string;
}

const props = defineProps<Props>();

const { value: model, errorMessage } = useField<string[] | undefined>(
  () => props.name,
  undefined,
);
</script>

<template>
  <FieldBaseComboBox v-bind="props" v-model="model" :error="errorMessage">
    <!-- Pass all the slots -->
    <template v-for="(_, name) in $slots" #[name]="scope">
      <slot :name v-bind="scope ?? {}" />
    </template>
  </FieldBaseComboBox>
</template>
