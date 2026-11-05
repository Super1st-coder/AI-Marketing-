<script lang="ts" setup>
import BrandsApi from "@/services/BrandsApi";
import ProjectsApi from "@/services/projects/ProjectsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const brand = (await BrandsApi.getOne(brandId)).data;
const project = (await ProjectsApi.getOne(brandId, projectId)).data;

usePageTitle(() =>
  t("routes.project-settings", {
    name: project.name,
    brand: brand.name,
  }),
);
</script>

<template>
  <ProjectForm :data="{ ...project }" />
</template>
