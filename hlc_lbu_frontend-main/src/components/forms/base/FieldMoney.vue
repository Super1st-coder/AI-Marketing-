<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldBaseMoneyProps } from "./FieldBaseMoney.vue";

interface Props extends FieldBaseMoneyProps {
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
  <FieldBaseMoney
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
  </FieldBaseMoney>
</template>
