<script lang="ts" setup>
import { DashboardGridLoadOptions } from "@/components/cards/CardDashboardGrid.vue";
import ProductsApi, { ProductData } from "@/services/ProductsApi";

const store = useBrandLayoutStore();
const { t } = useI18n();
usePageTitle(() => t("routes.products", { brand: store.brand?.name ?? "" }));

const brandId = useBrandId();

const search = ref<string | undefined>();
const itemsPerPage = ref(12);
const items = ref<ProductData[]>([]);
const itemsLength = ref(0);
const loading = ref(false);

// Fetch items from server
async function loadItems(options: DashboardGridLoadOptions) {
  loading.value = true;

  // Fetch the items
  const response = await ProductsApi.getList(brandId, {
    ...options.paginationOptions,
  });

  items.value = response.data;
  itemsLength.value = response.total;
  loading.value = false;

  options.scrollToTop?.();
}

// Initial load
await loadItems({
  paginationOptions: getDefaultPaginationOptions({
    itemsPerPage: itemsPerPage.value,
    search: search.value,
  }),
  itemsLength: itemsLength.value,
});

const isEmpty = ref(itemsLength.value === 0);
</script>

<template>
  <template v-if="isEmpty">
    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=faSh6NQ5wZY">
      <template #chip>
        {{ $t("products.tutorial.chip") }}
      </template>
      <template #title>
        {{ $t("products.tutorial.title") }}
      </template>
      <template #description>
        {{ $t("products.tutorial.description") }}
      </template>
      <template #actions>
        <Button :to="{ name: 'CreateProduct' }">
          {{ $t("products.tutorial.button") }}
        </Button>
      </template>
    </VideoTutorial>
  </template>
  <template v-else>
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=faSh6NQ5wZY"
    >
      {{ $t("products.products") }}
    </PageTitle>

    <CardDashboardGrid
      itemsIdKey="id"
      :items="items"
      spacing="md"
      :searchPlaceholder="$t('products.search-product')"
      :loading="loading"
      :itemsLength="itemsLength"
      :itemsPerPage="itemsPerPage"
      :sorters="[
        { key: 'name', label: $t('sorter.name') },
        { key: 'updatedAt', label: $t('sorter.last-updated') },
        { key: 'createdAt', label: $t('sorter.created-at') },
      ]"
      v-model:searchText="search"
      @update="loadItems"
    >
      <template #item="product">
        <ProductCard :data="product" interactable />
      </template>

      <template #actions>
        <PermissionGuard :requires="[{ name: 'PRODUCT', actions: ['C'] }]">
          <Button :to="{ name: 'CreateProduct' }" leftIcon="tabler-plus">
            {{ $t("products.create-product") }}
          </Button>
        </PermissionGuard>
      </template>
    </CardDashboardGrid>
  </template>
</template>
