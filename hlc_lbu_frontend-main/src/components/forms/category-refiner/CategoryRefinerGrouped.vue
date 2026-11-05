<script lang="ts" setup>
import { ModalAskLucaRefinerProps } from "@/components/forms/category-refiner/ModalAskLucaRefiner.vue";
import { RefinerCategory } from "./categoryRefinerTypes";

export interface CategoryRefinerGroupedProps {
  create?: boolean;
  newCategoryDefaultProps?: Partial<RefinerCategory>;
  askLuca?: Record<string, Omit<ModalAskLucaRefinerProps, "name">>;
  disabled?: boolean;
  //maxItems?: number;
  // Prop para recibir las categorías específicas a renderizar en este grupo
  categories: RefinerCategory[];
}

const props = defineProps<CategoryRefinerGroupedProps>();
</script>

<template>
  <CardGrid
    class="tw:items-start"
    :class="{ 'tw:pointer-events-none tw:opacity-50': props.disabled }"
  >
    <CategoryRefinerCard
      v-for="category in props.categories"
      :key="category.name"
      :category="category"
      :askLuca="props.askLuca?.[category.name]"
    />

    <CategoryRefinerCardEmpty
      v-if="props.create"
      :defaultProps="props.newCategoryDefaultProps"
    />
  </CardGrid>
</template>
