<script lang="ts" setup>
import { DashboardGridLoadOptions } from "@/components/cards/CardDashboardGrid.vue";
import CampaignsApi, { CampaignData } from "@/services/projects/CampaignsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;

usePageTitle(() => t("routes.campaigns", { project: project.name }));

const search = ref<string | undefined>();
const itemsPerPage = ref(12);
const items = ref<CampaignData[]>([]);
const itemsLength = ref(0);
const loading = ref(false);

// Fetch items from server
async function loadItems(options: DashboardGridLoadOptions) {
  loading.value = true;

  // Fetch the items
  const response = await CampaignsApi.getList(brandId, projectId, {
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
    <VideoTutorial videoSrc="https://www.youtube.com/watch?v=BzUZdoWNa28">
      <template #chip>
        {{ $t("campaigns.hub.videotutorial.chiptitle") }}</template
      >
      <template #title> {{ $t("campaigns.hub.videotutorial.title") }}</template>
      <template #description>
        {{ $t("campaigns.hub.videotutorial.description") }}
      </template>
      <template #actions>
        <PermissionGuard
          :requires="[{ name: 'CAMPAIGN_SETUP', actions: ['C'] }]"
        >
          <Button :to="{ name: 'CreateCampaign' }">
            {{ $t("campaigns.hub.buttoncreatetext") }}
          </Button>
        </PermissionGuard>
      </template>
    </VideoTutorial>
  </template>
  <template v-else>
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=BzUZdoWNa28"
    >
      {{ $t("campaigns.hub.title") }}
      <template #description>
        {{ $t("campaigns.hub.description") }}
      </template>
    </PageTitle>

    <CardDashboardGrid
      itemsIdKey="id"
      :items="items"
      spacing="md"
      :searchPlaceholder="$t('campaigns.hub.search-placeholder')"
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
      <template #item="campaign">
        <CampaignCard
          :campaign="campaign"
          :brandId="brandId"
          :projectId="projectId"
        />
      </template>

      <template #actions>
        <PermissionGuard
          :requires="[{ name: 'CAMPAIGN_SETUP', actions: ['C'] }]"
        >
          <Button :to="{ name: 'CreateCampaign' }" leftIcon="tabler-plus">
            {{ $t("campaigns.hub.buttoncreatetext") }}
          </Button>
        </PermissionGuard>
      </template>
    </CardDashboardGrid>
  </template>
</template>
