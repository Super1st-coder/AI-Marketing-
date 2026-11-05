<script setup lang="ts">
import ProjectsApi from "@/services/projects/ProjectsApi";
import { ProjectFormData } from "./ProjectForm.vue";
import BuyerPersonasApi, { BuyerPersonData } from "@/services/BuyerPersonasApi";
import { DashboardGridLoadOptions } from "../cards/CardDashboardGrid.vue";

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

const {
  data,
  saveData,
  goBack,
  goNext,
  currentFlatStepIndex,
  setDirtyStage,
  getIsStageDirty,
} = useMultiStepFormContext<ProjectFormData>();

const { confirm } = useConfirmModal();

const handleSelect = async (buyerPerson: BuyerPersonData) => {
  const isDirty = data.value.bperson?.id !== buyerPerson.id;
  let triggerGeneration = true;

  // Display and wait for the confirm modal if needed
  if (data.value.summary_generated) {
    if (isDirty || getIsStageDirty("summary")) {
      // Display the modal if the data is dirty
      const result = await confirm();
      if (result === "close") {
        return;
      }

      triggerGeneration = result === "continue";
    } else {
      // If the data is not dirty, do not trigger prompts
      triggerGeneration = false;
    }
  }

  const response = await ProjectsApi.setBuyerPerson(
    brandId,
    data.value.id,
    buyerPerson.id,
    { trigger_prompts: triggerGeneration },
  );

  // Save data and go next
  saveData({
    ...response.data,
    bperson: { ...buyerPerson, ...response.data.bperson },
  });
  setDirtyStage("summary", false);
  goNext({ isDirty: isDirty });
};
</script>

<template>
  <FormStepLayout>
    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=1tQk4N_BSnI"
    >
      {{ $t("projects.target-customer.title") }}

      <template #description>
        {{ $t("projects.target-customer.description") }}
      </template>
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
        <ProjectFormTargetCustomerCard
          :brandId="brandId"
          :projectId="data.id"
          :projectStep="currentFlatStepIndex"
          :buyerPerson="buyerPerson"
          @select="handleSelect"
        />
      </template>

      <template #actions>
        <Button
          leftIcon="tabler-plus"
          :to="{
            name: 'CreateBuyerPerson',
            query: { projectId: data.id, projectStep: currentFlatStepIndex },
          }"
        >
          {{ $t("buyer-person.create-target-customer") }}
        </Button>
      </template>
    </CardDashboardGrid>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
      </WizardCardActions>
    </template>

    <ModalConfirmRegeneration />
  </FormStepLayout>
</template>
