<script lang="ts" setup>
import { ProductData } from "@/services/ProductsApi";
import { RouteLocationRaw, RouterLink } from "vue-router";

interface Props {
  data: ProductData;
  interactable?: boolean;
}

const props = defineProps<Props>();

const route = computed<RouteLocationRaw | undefined>(() =>
  props.interactable
    ? {
        name: "ProductSettings",
        params: { productId: props.data.id },
      }
    : undefined,
);
</script>

<template>
  <CardBase class="tw:p-3">
    <!-- Image -->
    <component :is="interactable ? RouterLink : 'div'" :to="route">
      <CardDynamicImage
        class="tw:mb-4 tw:aspect-square"
        :src="data.thumbnail_url ?? undefined"
      />
    </component>

    <!-- Title -->
    <component :is="interactable ? RouterLink : 'div'" :to="route">
      <h2 class="tw:mb-2.5 tw:text-sm tw:font-bold">{{ data.name }}</h2>
    </component>

    <!-- Chips -->
    <ChipList>
      <ChipCompleted :completed="data.complete" />
      <ChipLocked :locked="data.locked" />
    </ChipList>
  </CardBase>
</template>
