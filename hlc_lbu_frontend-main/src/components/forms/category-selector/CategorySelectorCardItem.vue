<script lang="ts" setup>
import { useField } from "vee-validate";
import { CategorySelectorItem } from "./categorySelectorTypes";

interface CategoryRefinerFieldProps {
  name: string;
}

const props = defineProps<CategoryRefinerFieldProps>();

const { value: item } = useField<CategorySelectorItem>(
  () => props.name,
  undefined,
);

const name = item.value.name;

const { value: isChecked } = useField<boolean>(() => `${props.name}.checked`);
</script>

<template>
  <FieldBaseEditableText
    v-model="name"
    :editable="false"
    required
    type="textarea"
    checkable
    v-model:checked="isChecked"
  />
</template>
