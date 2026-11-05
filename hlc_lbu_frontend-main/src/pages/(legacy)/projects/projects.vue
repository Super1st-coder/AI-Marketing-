<script lang="ts" setup>
import ProjectsAPI from "@/services/legacy/ProjectsAPI";

const { data: projects } = await ProjectsAPI.getList();

const sortedProjects = computed(() =>
  [...projects].sort((a, b) => b.id - a.id),
);
</script>

<template>
  <WizardCard>
    <div class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]">
      <div>
        <WizardCardTitle>
          {{ $t("projects.title") }}
          <template #button>
            <HelpButton />
          </template>
        </WizardCardTitle>
      </div>

      <Button
        icon="tabler-arrow-right"
        size="md"
        :to="{ name: 'AdGenerationGettingStarted' }"
      >
        {{ $t("projects.create-new-project") }}
      </Button>

      <div class="tw:flex tw:flex-col tw:gap-8">
        <Card
          v-for="project in sortedProjects"
          padding="sm"
          class="tw:flex tw:flex-col tw:gap-4 tw:md:flex-row"
        >
          <div class="tw:flex tw:grow tw:flex-col tw:gap-3">
            <CardTitle>
              {{ project.name }}
            </CardTitle>
          </div>

          <div class="tw:flex tw:shrink-0 tw:flex-col tw:items-end tw:gap-3">
            <Button
              icon="tabler-arrow-right"
              size="md"
              :to="{ name: 'AdGenerationProcess', params: { id: project.id } }"
            >
              {{ $t("projects.see-project") }}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  </WizardCard>
</template>
