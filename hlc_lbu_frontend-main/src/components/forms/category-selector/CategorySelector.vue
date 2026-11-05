<script lang="ts" setup>
import { useField } from "vee-validate";
import { CategorySelector } from "./categorySelectorTypes";

interface CategoryRefinerFieldProps {
  name: string;
  label?: string;
}

const props = defineProps<CategoryRefinerFieldProps>();
const { t, te } = useI18n();

const { value: categories, errorMessage } = useField<CategorySelector[]>(
  () => props.name,
  undefined,
);

const selectedItemCount = computed(() => {
  return categories.value.reduce((acc, category) => {
    const selectedItems = category.items.filter((item) => item.checked);
    return acc + selectedItems.length;
  }, 0);
});
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-8">
    <div class="tw:flex tw:items-center tw:justify-between">
      <FieldLabel>
        {{ label }}
      </FieldLabel>

      <div
        class="tw:rounded-md tw:border tw:border-primary tw:px-3 tw:py-1.5 tw:text-2xl tw:font-extrabold tw:text-primary"
      >
        {{ selectedItemCount }}/3
      </div>
    </div>

    <CardGrid class="tw:items-start">
      <CategorySelectorCard
        v-for="(_category, index) in categories"
        :name="`${props.name}[${index}]`"
        :openCard="true"
      />
    </CardGrid>

    <Alert v-if="errorMessage" type="error" autoScroll>
      {{ te(errorMessage) ? t(errorMessage) : errorMessage }}
    </Alert>
  </div>
</template>
