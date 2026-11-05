<script lang="ts" setup>
import { ModalAskLucaRefinerProps } from "./ModalAskLucaRefiner.vue";
import { RefinerCategory } from "./categoryRefinerTypes";
import { useCategoryRefinerData } from "./useCategoryRefiner";

export interface CategoryRefinerProps {
  create?: boolean;
  newCategoryDefaultProps?: Partial<RefinerCategory>;
  askLuca?: Record<string, Omit<ModalAskLucaRefinerProps, "name">>;
  disabled?: boolean;
  errorMessage?: string;
}

defineProps<CategoryRefinerProps>();

const { data } = useCategoryRefinerData();
</script>

<template>
  <CardGrid
    class="tw:items-start"
    :class="{ 'tw:pointer-events-none tw:opacity-50': disabled }"
  >
    <CategoryRefinerCard
      v-for="category in data"
      :key="category.name"
      :category="category"
      :askLuca="askLuca?.[category.name]"
      :errorMessage="errorMessage"
    />

    <CategoryRefinerCardEmpty
      v-if="create"
      :defaultProps="newCategoryDefaultProps"
    />
  </CardGrid>
</template>
