<script lang="ts">
import { useField } from "vee-validate";
import { array, object, string, InferType, boolean, number } from "yup";

export const audienceSchema = object().shape({
  id: number().required(),
  selected: boolean(),
  title: string().required(),
  audience: string().required(),
  age: string().required(),
  gender: string().required(),
  location: string().required(),
  incomeLevel: string().required(),
  interests: array().of(string().required()).required(),
});

export type Audience = InferType<typeof audienceSchema>;
</script>

<script lang="ts" setup>
interface Props {
  name: string;
  selected?: boolean;
}

const props = defineProps<Props>();
const isExpanded = defineModel<boolean>("expanded");

const emits = defineEmits<{
  checked: [checked: boolean];
}>();

const { value: model } = useField<Audience>(props.name, undefined);
const { value: isSelected } = useField<boolean>(
  `${props.name}.selected`,
  undefined,
);

watch(isSelected, () => {
  emits("checked", isSelected.value);
});
</script>

<template>
  <SelectableCard
    v-model:selected="isSelected"
    expandable
    v-model:expanded="isExpanded"
  >
    <template #header>
      <CardTitle is="h2">
        {{ model.title }}
      </CardTitle>
    </template>

    <EditableCardSection
      :name="`${name}.audience`"
      title="Audience"
      icon="ic:round-people-alt"
      iconVariant="warning"
      editable
      class="card-audience"
    />

    <EditableCardSection
      :name="`${name}.age`"
      title="Age"
      icon="tabler-calendar-time"
      iconVariant="info"
      editable
      class="card-age"
    />

    <EditableCardSection
      :name="`${name}.gender`"
      title="Gender"
      icon="tabler-friends"
      iconVariant="success"
      editable
      class="card-gender"
    />

    <template v-if="isExpanded">
      <EditableCardSection
        :name="`${name}.location`"
        title="Location"
        icon="tabler-map-pin"
        iconVariant="warning"
        editable
        class="card-location"
      />

      <EditableCardSection
        :name="`${name}.incomeLevel`"
        title="Income Level"
        icon="tabler-coin"
        iconVariant="info"
        editable
        class="card-income-level"
      />

      <EditableCardSection
        :name="`${name}.interests`"
        title="Interests"
        icon="tabler-bulb"
        iconVariant="success"
        editable
        class="card-interests"
      />
    </template>
  </SelectableCard>
</template>
