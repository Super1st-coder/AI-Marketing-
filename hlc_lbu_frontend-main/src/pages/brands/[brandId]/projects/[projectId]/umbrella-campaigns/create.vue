<script lang="ts" setup>
import ProjectsApi from "@/services/projects/ProjectsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;

usePageTitle(() =>
  t("routes.create-umbrella-campaign", { project: project.name }),
);
</script>

<template>
  <UmbrellaCampaignForm />
</template>
