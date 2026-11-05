<script lang="ts" setup generic="T">
const multiStepData = useMultiStepFormContext();

const visibleSteps = computed(() =>
  multiStepData.steps.value.filter((step) => !step.invisible),
);
</script>

<template>
  <div class="tw:flex tw:min-h-[calc(100vh-66px)]">
    <Sidebar>
      <slot name="sidebarBefore" />

      <template #header>
        <SidebarTitle v-if="$slots.sidebarTitle">
          <slot name="sidebarTitle" />
        </SidebarTitle>

        <slot name="sidebarHeader" />
      </template>

      <SidebarLinkWrapper>
        <Tooltip
          v-for="step in visibleSteps"
          :disabled="!multiStepData.getHasLinkTooltip(step)"
          placement="right"
          :maxWidth="800"
        >
          <SidebarLink
            :disabled="multiStepData.getIsLinkDisabled(step)"
            @click="multiStepData.handleLinkClick(step)"
            :icon="step.icon"
            :hasAlert="multiStepData.getHasLinkAlert(step)"
            :variant="
              multiStepData.getIsLinkCompleted(step) ? 'success' : 'normal'
            "
            :selected="multiStepData.getIsLinkSelected(step)"
          >
            {{ step.label }}
          </SidebarLink>

          <template #content>
            <!-- Dynamic slot -->
            <slot :name="`${step.name}.tooltip`" />

            <!-- Simpler slot -->
            <slot name="tooltip" :step="step" />
          </template>
        </Tooltip>
      </SidebarLinkWrapper>

      <template #footer>
        <slot name="sidebarFooter" />
      </template>
    </Sidebar>

    <GradientBackground class="tw:w-full">
      <slot v-bind="multiStepData" />
    </GradientBackground>
  </div>
</template>
