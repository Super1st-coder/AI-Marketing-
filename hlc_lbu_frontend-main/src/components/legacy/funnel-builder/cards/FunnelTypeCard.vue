<script lang="ts" setup>
import { useField } from "vee-validate";

interface Props {
  name: string;
  value: string;
}

const props = defineProps<Props>();

const { value: framework } = useField<string | undefined>(
  () => props.name,
  undefined,
);
const isSelected = computed({
  get: () => framework.value === props.value,
  set: (value) => {
    framework.value = value ? props.value : undefined;
  },
});
</script>

<template>
  <SelectableCard v-model:selected="isSelected">
    <template #header>
      <CardTitle is="h2">
        <slot name="title" />
      </CardTitle>
    </template>

    <Separator />

    <CardParagraph variant="light">
      <slot name="description" />
    </CardParagraph>
  </SelectableCard>
</template>
