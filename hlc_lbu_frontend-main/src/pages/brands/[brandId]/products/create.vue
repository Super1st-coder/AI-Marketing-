<script lang="ts" setup>
import BrandsApi from "@/services/BrandsApi";

const { t } = useI18n();
const brandId = useBrandId();
const brand = (await BrandsApi.getOne(brandId)).data;

usePageTitle(() => t("routes.create-product", { brand: brand.name }));
</script>

<template>
  <ProductForm />
</template>
