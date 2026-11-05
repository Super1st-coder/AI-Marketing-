<script lang="ts" setup>
import { RefinerItem } from "./categoryRefinerTypes";

const props = defineProps<{ index: number; item: RefinerItem }>();
const items = defineModel<RefinerItem[]>("items", { required: true });

const name = computed({
  get: () => {
    return props.item.name;
  },
  set: (value) => {
    items.value[props.index].name = value;
  },
});

const checked = computed({
  get: () => {
    return props.item.checked;
  },
  set: (value) => {
    items.value[props.index].checked = value;
  },
});
</script>

<template>
  <FieldBaseEditableText
    v-model="name"
    v-model:checked="checked"
    checkable
    required
    type="textarea"
  />
</template>
