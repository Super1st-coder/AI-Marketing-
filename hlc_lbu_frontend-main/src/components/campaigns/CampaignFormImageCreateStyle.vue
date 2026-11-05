<script lang="ts" setup>
import CampaignsApi, {
  CampaingStyleData,
} from "@/services/projects/CampaignsApi";
import { CampaignFormData } from "./CampaignForm.vue";

const emit = defineEmits<{
  goBack: [];
  goNext: [];
}>();

const { data, saveData } = useMultiStepFormContext<CampaignFormData>();

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = data.value.id;

const handleStyleSelected = async (selectedCampaign: CampaingStyleData) => {
  await CampaignsApi.SetImageStyleByCampaign(
    brandId,
    projectId,
    campaignId,
    selectedCampaign.id,
  );

  const genereteAtribbute = await CampaignsApi.GenerateCampaignImageAttributes(
    brandId,
    projectId,
    campaignId,
  );

  saveData(genereteAtribbute.data);
  emit("goNext");
};
</script>

<template>
  <FormStepLayout>
    <StyleSelectionGrid
      :setStyle="handleStyleSelected"
      helpVideoUrl="https://www.youtube.com/watch?v=rZD4x4M9540"
    >
      <template #title>
        {{ $t("campaigns.campaignsimage.image.style.title") }}
      </template>

      <template #description>
        {{ $t("campaigns.campaignsimage.image.style.description") }}
      </template>
    </StyleSelectionGrid>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="emit('goBack')" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
