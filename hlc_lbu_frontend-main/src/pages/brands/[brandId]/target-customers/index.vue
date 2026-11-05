<script lang="ts" setup>
import { DashboardGridLoadOptions } from "@/components/cards/CardDashboardGrid.vue";
import BuyerPersonasApi, { BuyerPersonData } from "@/services/BuyerPersonasApi";

const store = useBrandLayoutStore();
const { t } = useI18n();
usePageTitle(() =>
  t("routes.target-customers", { brand: store.brand?.name ?? "" }),
);

const brandId = useBrandId();

const search = ref<string | undefined>();
const itemsPerPage = ref(12);
const items = ref<BuyerPersonData[]>([]);
const itemsLength = ref(0);
const loading = ref(false);

// Fetch items from server
async function loadItems(options: DashboardGridLoadOptions) {
  loading.value = true;

  // Fetch the items
  const response = await BuyerPersonasApi.getList(brandId, {
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
    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=wzsdpyJ2Eok">
      <template #chip>
        {{ $t("buyer-person.tutorial.chip") }}
      </template>
      <template #title>
        {{ $t("buyer-person.tutorial.title") }}
      </template>
      <template #description>
        {{ $t("buyer-person.tutorial.description") }}
      </template>
      <template #actions>
        <Button :to="{ name: 'CreateBuyerPerson' }">
          {{ $t("buyer-person.tutorial.button") }}
        </Button>
      </template>
    </VideoTutorial>
  </template>
  <template v-else>
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=wzsdpyJ2Eok"
    >
      {{ $t("buyer-person.target-customers") }}
    </PageTitle>

    <CardDashboardGrid
      itemsIdKey="id"
      :items="items"
      spacing="md"
      :searchPlaceholder="$t('buyer-person.search-target-customer')"
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
      <template #item="buyerPerson">
        <TargetCustomerCard :data="buyerPerson" interactable />
      </template>

      <template #actions>
        <PermissionGuard
          :requires="[{ name: 'TARGET_CUSTOMER', actions: ['C'] }]"
        >
          <Button :to="{ name: 'CreateBuyerPerson' }" leftIcon="tabler-plus">
            {{ $t("buyer-person.create-target-customer") }}
          </Button>
        </PermissionGuard>
      </template>
    </CardDashboardGrid>
  </template>
</template>
