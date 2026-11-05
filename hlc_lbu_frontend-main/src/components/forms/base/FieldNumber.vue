<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldBaseNumberProps } from "./FieldBaseNumber.vue";

interface Props extends FieldBaseNumberProps {
  name: string;
}

const props = defineProps<Props>();

const {
  value: model,
  errorMessage,
  handleChange: _handleChange,
  handleBlur: _handleBlur,
} = useField<number | undefined>(() => props.name, undefined);

const handleChange = (e: Event | unknown) => {
  _handleChange(e);
};

const handleBlur = (e: Event | undefined) => {
  _handleBlur(e);
};
</script>

<template>
  <FieldBaseNumber
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
  </FieldBaseNumber>
</template>
