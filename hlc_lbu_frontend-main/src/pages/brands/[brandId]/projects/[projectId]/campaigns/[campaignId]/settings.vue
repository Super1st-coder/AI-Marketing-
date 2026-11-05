<script lang="ts" setup>
import CampaignsApi from "@/services/projects/CampaignsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;
const campaign = (await CampaignsApi.getOne(brandId, projectId, campaignId))
  .data;

usePageTitle(() =>
  t("routes.campaign-settings", {
    name: campaign.name,
    project: project.name,
  }),
);
</script>

<template>
  <CampaignForm :data="{ ...campaign }" />
</template>
