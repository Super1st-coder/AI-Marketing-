<script lang="ts" setup>
import { useField } from "vee-validate";
import { FieldBaseAutocompleteProps } from "./FieldBaseAutocomplete.vue";

interface Props extends FieldBaseAutocompleteProps {
  name: string;
}

const props = defineProps<Props>();

const search = defineModel<string>({ required: false });

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
  <FieldBaseAutocomplete
    v-bind="props"
    v-model="model"
    v-model:search="search"
    @blur="handleBlur"
    :error="errorMessage"
  >
    <!-- Pass all the slots -->
    <template v-for="(_, name) in $slots" #[name]="scope">
      <slot :name v-bind="scope ?? {}" />
    </template>
  </FieldBaseAutocomplete>
</template>
