<script lang="ts" setup>
import ProjectsApi from "@/services/projects/ProjectsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const project = (await ProjectsApi.getOne(brandId, projectId)).data;

usePageTitle(() => t("routes.project", { project: project.name }));
</script>

<template></template>
