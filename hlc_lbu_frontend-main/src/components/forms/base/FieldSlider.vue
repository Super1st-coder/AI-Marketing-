<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldBaseSliderProps } from "./FieldBaseSlider.vue";

interface Props extends FieldBaseSliderProps {
  name: string;
}

const props = defineProps<Props>();

const {
  value: model,
  errorMessage,
  handleChange: _handleChange,
  handleBlur: _handleBlur,
} = useField<number>(() => props.name, undefined);

const handleChange = (value: number) => {
  _handleChange(value);
};

const handleBlur = (e: Event) => {
  _handleBlur(e);
};
</script>

<template>
  <FieldBaseSlider
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
  </FieldBaseSlider>
</template>
