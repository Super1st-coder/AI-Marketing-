<script lang="ts" setup>
import { UmbrellaCampaignFormData } from "./UmbrellaCampaignForm.vue";
import UmbrellaCampaignsApi from "@/services/projects/UmbrellaCampaignsApi";
import { CampaingStyleData } from "@/services/projects/CampaignsApi";

const emit = defineEmits<{
  goBack: [];
  goNext: [];
}>();

const { data, saveData } = useMultiStepFormContext<UmbrellaCampaignFormData>();

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = data.value.id;

const handleSetStyle = async (selectedCampaign: CampaingStyleData) => {
  await UmbrellaCampaignsApi.setImageStyle(
    brandId,
    projectId,
    campaignId,
    selectedCampaign.id,
  );

  const generatedAttributes =
    await UmbrellaCampaignsApi.generateImageAttributes(
      brandId,
      projectId,
      campaignId,
    );

  saveData(generatedAttributes.data);
  emit("goNext");
};
</script>

<template>
  <FormStepLayout>
    <StyleSelectionGrid
      :setStyle="handleSetStyle"
      helpVideoUrl="https://www.youtube.com/watch?v=uB81rH44TZU"
    >
      <template #title>
        {{ $t("umbrella-campaign.step-image.style-image.title") }}
      </template>

      <template #description>
        {{ $t("umbrella-campaign.step-image.style-image.description") }}
      </template>
    </StyleSelectionGrid>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="emit('goBack')" />
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
