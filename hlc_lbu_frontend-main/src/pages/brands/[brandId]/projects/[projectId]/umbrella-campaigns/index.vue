<script lang="ts" setup>
import { DashboardGridLoadOptions } from "@/components/cards/CardDashboardGrid.vue";
import ProjectsApi from "@/services/projects/ProjectsApi";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
} from "@/services/projects/UmbrellaCampaignsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;

usePageTitle(() => t("routes.umbrella-campaigns", { project: project.name }));

const search = ref<string | undefined>();
const itemsPerPage = ref(12);
const items = ref<UmbrellaCampaignData[]>([]);
const itemsLength = ref(0);
const loading = ref(false);

// Fetch items from server
async function loadItems(options: DashboardGridLoadOptions) {
  loading.value = true;

  // Fetch the items
  const response = await UmbrellaCampaignsApi.getList(brandId, projectId, {
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
    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=DHVzWMhmNH4">
      <template #chip>
        {{ $t("umbrella-campaign.index-page.tutorial.chip") }}</template
      >
      <template #title>
        {{ $t("umbrella-campaign.index-page.tutorial.title") }}</template
      >
      <template #description>
        {{ $t("umbrella-campaign.index-page.tutorial.description") }}
      </template>
      <template #actions>
        <Button :to="{ name: 'CreateUmbrellaCampaign' }">
          {{ $t("umbrella-campaign.index-page.button-create") }}
        </Button>
      </template>
    </VideoTutorial>
  </template>
  <template v-else>
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=DHVzWMhmNH4"
    >
      {{ $t("umbrella-campaign.index-page.title") }}
      <template #description>
        {{ $t("umbrella-campaign.index-page.description") }}
      </template>
    </PageTitle>

    <CardDashboardGrid
      itemsIdKey="id"
      :items="items"
      spacing="md"
      :searchPlaceholder="$t('umbrella-campaign.index-page.search-placeholder')"
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
      <template #item="umbrellaCampaign">
        <UmbrellaCampaignCard :data="umbrellaCampaign" interactable />
      </template>

      <template #actions>
        <PermissionGuard
          :requires="[{ name: 'UMBRELLA_CAMPAIGN', actions: ['C'] }]"
        >
          <Button
            :to="{ name: 'CreateUmbrellaCampaign' }"
            leftIcon="tabler-plus"
          >
            {{ $t("umbrella-campaign.index-page.button-create") }}
          </Button>
        </PermissionGuard>
      </template>
    </CardDashboardGrid>
  </template>
</template>
