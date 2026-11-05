<script lang="ts">
import { useField } from "vee-validate";
import { array, object, string, InferType, mixed, boolean, number } from "yup";

export const productSchema = object().shape({
  id: number().required(),
  selected: boolean(),
  title: string().required(),
  coreCharacteristic: string().required(),
  advantage: string().required(),
  description: string().required(),
  benefit: string().required(),
  details: array().of(string().required()).required(),
  file: mixed(),
});

export type Product = InferType<typeof productSchema>;
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
  checked: [checked: boolean, value: Product];
}>();

const { value: model } = useField<Product>(props.name, undefined);
const { value: isSelected } = useField<boolean>(
  `${props.name}.selected`,
  undefined,
);

watch(isSelected, () => {
  emits("checked", isSelected.value, model.value);
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

    <Separator />

    <button
      class="tw:flex tw:flex-col tw:gap-5 tw:text-left"
      type="button"
      @click="isOpen = true"
    >
      <div class="card-title-and-paragraph">
        <CardTitle>
          {{ $t("process.product.card.core-characteristic") }}
        </CardTitle>

        <CardParagraph variant="light">
          {{ model.coreCharacteristic }}
        </CardParagraph>
      </div>

      <template v-if="isExpanded">
        <Separator />

        <ProductCardSections :name="name" />
      </template>
    </button>

    <ModalStandard v-model="isOpen">
      <template #header>
        <CardTitle is="h2"> {{ model.title }} </CardTitle>
        <CardParagraph variant="light">
          {{ model.coreCharacteristic }}
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
        <ProductCardSections :name="name" editable />
      </template>

      <template #right>
        <div class="flex-center tw:h-full tw:w-full">
          <FieldFile
            :name="`${name}.file`"
            rules="mimes:image/*"
            :label="$t('process.product.upload-product-image')"
          />
        </div>
      </template>
    </ModalStandard>
  </SelectableCard>
</template>
