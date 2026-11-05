<script lang="ts" setup>
import BrandsApi from "@/services/BrandsApi";
import BuyerPersonasApi from "@/services/BuyerPersonasApi";

const { t } = useI18n();
const brandId = useBrandId();
const buyerPersonId = useBuyerPersonId();
const brand = (await BrandsApi.getOne(brandId)).data;
const buyerPerson = (await BuyerPersonasApi.getOne(brandId, buyerPersonId))
  .data;

usePageTitle(() =>
  t("routes.target-customer-settings", {
    name: buyerPerson.name,
    brand: brand.name,
  }),
);
</script>

<template>
  <TargetCustomerForm :data="{ ...buyerPerson, brandId }" />
</template>
