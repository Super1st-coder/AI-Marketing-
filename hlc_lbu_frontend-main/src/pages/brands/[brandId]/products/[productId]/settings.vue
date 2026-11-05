<script lang="ts" setup>
import BrandsApi from "@/services/BrandsApi";
import ProductsApi from "@/services/ProductsApi";

const { t } = useI18n();
const brandId = useBrandId();
const productId = useProductId();
const brand = (await BrandsApi.getOne(brandId)).data;
const product = (await ProductsApi.getOne(brandId, productId)).data;

usePageTitle(() =>
  t("routes.product-settings", {
    name: product.name,
    brand: brand.name,
  }),
);
</script>

<template>
  <ProductForm :data="{ ...product }" />
</template>
