<script lang="ts" setup>
import { ProductData } from "@/services/ProductsApi";
import { getSummaryRefinerCategories } from "../forms/category-refiner/categoryRefinerTypes";
import { productRefinerStyles } from "../products/productContants";

const props = defineProps<{
  projectId: number;
  projectStep: number;
  brandId: number;
  product: ProductData;
}>();

const isModalOpen = ref(false);
const emit = defineEmits<{ select: [product: ProductData] }>();

const mandatoryCategories = getSummaryRefinerCategories(
  props.product.mandatory_attributes_saved,
  props.product.mandatory_attributes_generated,
);
const optionalCategories = getSummaryRefinerCategories(
  props.product.optional_attributes_saved,
  props.product.optional_attributes_generated,
);
const categories = [...mandatoryCategories, ...optionalCategories];
</script>

<template>
  <ProductCard
    :data="product"
    is="button"
    type="button"
    class="tw:text-left"
    @click="isModalOpen = true"
  />

  <ProjectFormSelectionModal
    v-model="isModalOpen"
    :completed="product.complete"
    :name="product.name"
    :description="product.product_story || product.description"
    :categories="categories"
    :categoriesStyles="productRefinerStyles"
    :images="
      product.images?.map((image) => image.url) ??
      (product.thumbnail_url ? [product.thumbnail_url] : [])
    "
    :editRoute="{
      name: 'ProductSettings',
      params: { productId: product.id },
      query: { projectId, projectStep },
    }"
    @select="emit('select', product)"
  />
</template>
