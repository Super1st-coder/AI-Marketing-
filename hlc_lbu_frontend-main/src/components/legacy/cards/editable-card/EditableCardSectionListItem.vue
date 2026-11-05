<script lang="ts" setup>
import { useField } from "vee-validate";

interface Props {
  name: string;
  index: number;
  disabled?: boolean;
}

const props = defineProps<Props>();
const { value: values, setValue } = useField<string[]>(
  () => props.name,
  undefined,
);

const text = ref<string>(values.value[props.index]);

watch(text, (value) => {
  // Replace text in the array
  const newValues = values.value.map((item, index) => {
    if (index === props.index) {
      return value;
    }

    return item;
  });

  // Save it
  setValue(newValues);
});
</script>

<template>
  <FieldBaseEditableText
    v-model="text"
    type="textarea"
    preventScroll
    :disabled="disabled"
  />
</template>
