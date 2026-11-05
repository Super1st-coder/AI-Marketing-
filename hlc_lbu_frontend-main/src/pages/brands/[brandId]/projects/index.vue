<script lang="ts" setup>
import { DashboardGridLoadOptions } from "@/components/cards/CardDashboardGrid.vue";
import ProjectsApi, { ProyectData } from "@/services/projects/ProjectsApi";

const store = useBrandLayoutStore();
const { t } = useI18n();
usePageTitle(() => t("routes.projects", { brand: store.brand?.name ?? "" }));

const brandId = useBrandId();

const search = ref<string | undefined>();
const itemsPerPage = ref(12);
const items = ref<ProyectData[]>([]);
const itemsLength = ref(0);
const loading = ref(false);

// Fetch items from server
async function loadItems(options: DashboardGridLoadOptions) {
  loading.value = true;

  // Fetch the items
  const response = await ProjectsApi.getList(brandId, {
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
    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=Htu-ELhzTAY">
      <template #chip>
        {{ $t("projects.tutorial.chip") }}
      </template>
      <template #title>
        {{ $t("projects.tutorial.title") }}
      </template>
      <template #description>
        {{ $t("projects.tutorial.description") }}
      </template>
      <template #actions>
        <Button :to="{ name: 'CreateProject' }">
          {{ $t("projects.tutorial.button") }}
        </Button>
      </template>
    </VideoTutorial>
  </template>
  <template v-else>
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=Htu-ELhzTAY"
    >
      {{ $t("projects.title") }}

      <template #description>
        {{ $t("projects.description") }}
      </template>
    </PageTitle>

    <CardDashboardGrid
      itemsIdKey="id"
      :items="items"
      spacing="md"
      :searchPlaceholder="$t('projects.search-project')"
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
      <template #item="project">
        <ProjectCard :data="project" />
      </template>

      <template #actions>
        <PermissionGuard :requires="[{ name: 'PROJECT', actions: ['C'] }]">
          <Button leftIcon="tabler-plus" :to="{ name: 'CreateProject' }">
            {{ $t("projects.create-a-new-project") }}
          </Button>
        </PermissionGuard>
      </template>
    </CardDashboardGrid>
  </template>
</template>
