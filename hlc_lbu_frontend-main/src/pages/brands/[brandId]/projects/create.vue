<script lang="ts" setup>
import BrandsApi from "@/services/BrandsApi";

const { t } = useI18n();
const brandId = useBrandId();
const brand = (await BrandsApi.getOne(brandId)).data;

usePageTitle(() => t("routes.create-project", { brand: brand.name }));
</script>

<template>
  <ProjectForm />
</template>
