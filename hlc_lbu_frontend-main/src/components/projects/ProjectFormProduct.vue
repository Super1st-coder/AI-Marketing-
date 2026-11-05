<script setup lang="ts">
import ProductsApi, { ProductData } from "@/services/ProductsApi";
import { ProjectFormData } from "./ProjectForm.vue";
import ProjectsApi from "@/services/projects/ProjectsApi";
import { DashboardGridLoadOptions } from "../cards/CardDashboardGrid.vue";

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

const { data, saveData, goBack, goNext, currentFlatStepIndex, setDirtyStage } =
  useMultiStepFormContext<ProjectFormData>();

const handleSelect = async (product: ProductData) => {
  const isDirty = data.value.product?.id !== product.id;

  const response = await ProjectsApi.setProduct(
    brandId,
    data.value.id,
    product.id,
  );

  // Save data and go next
  if (isDirty) {
    setDirtyStage("summary", true);
  }
  saveData({ ...response.data, product: { ...product } });
  goNext({ isDirty });
};
</script>

<template>
  <FormStepLayout>
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=vYumstoB-G4"
    >
      {{ $t("projects.product.title") }}

      <template #description>
        {{ $t("projects.product.description") }}
      </template>
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
        <ProjectFormProductCard
          :brandId="brandId"
          :projectId="data.id"
          :product="product"
          :projectStep="currentFlatStepIndex"
          @select="handleSelect"
        />
      </template>

      <template #actions>
        <Button
          leftIcon="tabler-plus"
          :to="{
            name: 'CreateProduct',
            query: { projectId: data.id, projectStep: currentFlatStepIndex },
          }"
        >
          {{ $t("products.create-product") }}
        </Button>
      </template>
    </CardDashboardGrid>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
