<script lang="ts" setup>
import ProjectsAPI from "@/services/legacy/ProjectsAPI";
import { useRoute } from "vue-router";

const store = useAdGenerationStore();
const route = useRoute();

// Fetch the project
const projectId = parseInt(route.params.id as string);
const project = await ProjectsAPI.getOne(projectId);

// Set the data
store.setData(projectId, project.data);
</script>

<template>
  <AddGenerationFirstPhase v-if="store.currentScreen === 'firstPhase'" />
  <AddGenerationFirstPhaseReady
    v-else-if="store.currentScreen === 'firstPhaseReady'"
  />
  <AddGenerationSecondPhasePresentation
    v-else-if="store.currentScreen === 'secondPhasePresentation'"
  />
  <AddGenerationSecondPhase v-else-if="store.currentScreen === 'secondPhase'" />
  <AddGenerationSecondPhaseReady
    v-else-if="store.currentScreen === 'secondPhaseReady'"
  />
  <AddGenerationThirdPhasePresentation
    v-else-if="store.currentScreen === 'thirdPhasePresentation'"
  />
  <AddGenerationThirdPhase v-else-if="store.currentScreen === 'thirdPhase'" />
</template>
