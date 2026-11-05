<script lang="ts" setup>
import { DashboardGridLoadOptions } from "@/components/cards/CardDashboardGrid.vue";
import NewBrandsApi, { BrandData } from "@/services/NewBrandsApi";

const { t } = useI18n();
usePageTitle(() => t("routes.brands"));

const search = ref<string | undefined>();
const itemsPerPage = ref(12);
const items = ref<BrandData[]>([]);
const itemsLength = ref(0);
const loading = ref(false);

// Fetch items from server
async function loadItems(options: DashboardGridLoadOptions) {
  loading.value = true;

  // Fetch the items
  const response = await NewBrandsApi.getList({
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
  <ContainerDashboard>
    <template v-if="isEmpty">
      <VideoTutorial videoSrc="https://www.youtube.com/watch?v=ugqIskTzMD4">
        <template #title>
          {{ $t("brands.tutorial.title") }}
        </template>

        <template #description>
          {{ $t("brands.tutorial.description") }}
        </template>

        <template #actionsDescription>
          {{ $t("brands.tutorial.actions-description") }}
        </template>

        <template #actions>
          <PermissionGuard :requires="[{ name: 'BRAND', actions: ['C'] }]">
            <Button leftIcon="tabler:plus" :to="{ name: 'CreateBrand' }">
              {{ $t("brands.tutorial.button") }}
            </Button>
          </PermissionGuard>
        </template>
      </VideoTutorial>
    </template>
    <template v-else>
      <PageTitle
        helpButton
        helpVideoUrl="https://www.youtube.com/watch?v=ugqIskTzMD4"
      >
        {{ $t("brands.my-brands") }}

        <template #description>
          {{ $t("brands.home.description") }}
        </template>
      </PageTitle>

      <CardDashboardGrid
        itemsIdKey="id"
        :items="items"
        spacing="md"
        :searchPlaceholder="$t('brands.search-brand')"
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
        <template #item="brand">
          <NewBrandCard :data="brand" />
        </template>

        <template #actions>
          <PermissionGuard :requires="[{ name: 'BRAND', actions: ['C'] }]">
            <Button leftIcon="tabler-plus" :to="{ name: 'CreateBrand' }">
              {{ $t("brands.create-a-new-brand") }}
            </Button>
          </PermissionGuard>
        </template>
      </CardDashboardGrid>
    </template>
  </ContainerDashboard>
</template>
