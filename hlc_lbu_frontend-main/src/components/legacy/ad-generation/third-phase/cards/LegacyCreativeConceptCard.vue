<script lang="ts">
import { useField } from "vee-validate";
import { object, string, InferType, boolean, number } from "yup";

export const creativeConceptSchema = object().shape({
  id: number().required(),
  selected: boolean(),
  title: string().required(),
  description: string().required(),
  concept: string().required(),
  message: string().required(),
  slogan: string().required(),
});

export type CreativeConcept = InferType<typeof creativeConceptSchema>;
</script>

<script lang="ts" setup>
interface Props {
  name: string;
  selected?: boolean;
}

const props = defineProps<Props>();
const isOpen = ref(false);
const isExpanded = defineModel<boolean>("expanded");

const emits = defineEmits<{
  checked: [checked: boolean];
}>();

const { value: model } = useField<CreativeConcept>(props.name, undefined);
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

    <ButtonAskLuca v-if="isExpanded" />

    <button
      class="tw:flex tw:flex-col tw:gap-5 tw:text-left"
      type="button"
      @click="isOpen = true"
    >
      <template v-if="!isExpanded">
        <Separator />

        <div class="card-description">
          <CardParagraph variant="light">
            {{ model.concept }}
          </CardParagraph>
        </div>
      </template>

      <template v-if="isExpanded">
        <Separator />

        <LegacyCreativeConceptCardSections :name="name" />
      </template>
    </button>

    <ModalStandard v-model="isOpen">
      <template #header>
        <CardTitle is="h2"> {{ model.title }} </CardTitle>
        <CardParagraph variant="light">
          {{ model.description }}
        </CardParagraph>
      </template>

      <template #headerActions>
        <ButtonAskLuca class="tw:grow" />
        <ButtonCheck
          @click="isSelected = !isSelected"
          type="button"
          :checked="isSelected"
        />
      </template>

      <template #body>
        <LegacyCreativeConceptCardSections :name="name" editable />
      </template>
    </ModalStandard>
  </SelectableCard>
</template>
