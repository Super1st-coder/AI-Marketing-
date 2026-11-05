<script lang="ts" setup>
import { UmbrellaCampaignData } from "@/services/projects/UmbrellaCampaignsApi";

const props = defineProps<{
  projectId: number;
  umbrellaCampaign: UmbrellaCampaignData;
  campaignId: number;
  campaignStep: number;
}>();

const { t: $t } = useI18n();
const isModalOpen = ref(false);
const emit = defineEmits<{
  select: [umbrellaCampaign: UmbrellaCampaignData];
}>();

const name = computed(
  () =>
    props.umbrellaCampaign.name ??
    $t("campaigns.select-umbrella-campaign.titlenotavailablecardtext"),
);

const description = computed(
  () => props.umbrellaCampaign.preferred_umbrella_campaign?.description,
);
</script>

<template>
  <UmbrellaCampaignCard
    :data="umbrellaCampaign"
    is="button"
    type="button"
    class="tw:text-left"
    @click="isModalOpen = true"
  />

  <CampaignFormSelectionModal
    v-model="isModalOpen"
    :completed="umbrellaCampaign.complete"
    :name="name"
    :description="description"
    :editRoute="{
      name: 'UmbrellaCampaignSettings',
      params: { umbrellaCampaignId: umbrellaCampaign.id },
      query: { projectId, campaignId, campaignStep },
    }"
    @select="emit('select', umbrellaCampaign)"
  >
    <UmbrellaCampaignFormSummaryCards :umbrellaCampaign="umbrellaCampaign" />
  </CampaignFormSelectionModal>
</template>
