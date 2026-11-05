<script lang="ts" setup>
import ProjectsApi from "@/services/projects/ProjectsApi";
import UmbrellaCampaignsApi from "@/services/projects/UmbrellaCampaignsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const umbrellaCampaignId = useUmbrellaCampaignId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;
const umbrellaCampaign = (
  await UmbrellaCampaignsApi.getOne(brandId, projectId, umbrellaCampaignId)
).data;

usePageTitle(() =>
  t("routes.umbrella-campaign-settings", {
    name: umbrellaCampaign.name,
    project: project.name,
  }),
);
</script>

<template>
  <UmbrellaCampaignForm :data="{ ...umbrellaCampaign }" />
</template>
