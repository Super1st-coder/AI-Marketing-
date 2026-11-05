<script setup lang="ts">
import CampaignsApi from "@/services/projects/CampaignsApi";
import { CampaignFormData } from "./CampaignForm.vue";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
} from "@/services/projects/UmbrellaCampaignsApi";
import { DashboardGridLoadOptions } from "../cards/CardDashboardGrid.vue";

const brandId = useBrandId();
const projectId = useProjectId();

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

const { data, saveData, goBack, goNext, currentFlatStepIndex } =
  useMultiStepFormContext<CampaignFormData>();

const handleSelect = async (umbrellaCampaign: UmbrellaCampaignData) => {
  const response = await CampaignsApi.setUmbrellaCampaign(
    brandId,
    projectId,
    data.value.id,
    umbrellaCampaign.id,
  );

  saveData({ ...response.data });
  goNext();
};
</script>

<template>
  <FormStepLayout>
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=G2GeX9Duum4"
    >
      {{ $t("campaigns.select-umbrella-campaign.title") }}
      <template #description>
        {{ $t("campaigns.select-umbrella-campaign.subtitle") }}
      </template>
    </PageTitle>

    <CardDashboardGrid
      itemsIdKey="id"
      :items="items"
      spacing="md"
      :searchPlaceholder="
        $t('campaigns.select-umbrella-campaign.placeholdersearch')
      "
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
        <CampaignFormUmbrellaCampaignCard
          :projectId="projectId"
          :umbrellaCampaign="umbrellaCampaign"
          :campaignId="data.id"
          :campaignStep="currentFlatStepIndex"
          @select="handleSelect"
        />
      </template>

      <template #actions>
        <Button
          leftIcon="tabler-plus"
          :to="{
            name: 'CreateUmbrellaCampaign',
            query: {
              projectId,
              campaignId: data.id,
              campaignStep: currentFlatStepIndex,
            },
          }"
        >
          {{ $t("campaigns.select-umbrella-campaign.buttontext") }}
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
