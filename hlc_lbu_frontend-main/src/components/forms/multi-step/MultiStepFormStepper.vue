<script lang="ts" setup>
import { FormStepperStep } from "./FormStepperBase.vue";

const props = defineProps<{
  parentStepName?: string;
}>();

const {
  steps,
  flattenSteps,
  handleLinkClick,
  getIsLinkCompleted,
  getIsLinkSelected,
  getIsLinkDisabled,
} = useMultiStepFormContext();

const visibleSteps = computed(() => {
  if (props.parentStepName) {
    const parent = steps.value.find(
      (step) => step.name === props.parentStepName,
    );
    const children = (parent?.children ?? []).filter((step) => !step.invisible);

    return children.map((child) => {
      const flatStep = flattenSteps.value.find(
        (step) => step.name === child.name,
      );

      return flatStep ?? child;
    });
  }

  return steps.value.filter((step) => !step.invisible);
});

const data = computed(() =>
  visibleSteps.value.map<FormStepperStep>((step) => {
    // Is this step completed?
    let completed = getIsLinkCompleted(step);

    // Is the form currently in this step?
    let current = getIsLinkSelected(step);

    // Function to call when the step is clicked
    const _handleLinkClick = () => {
      handleLinkClick(step);
    };

    const disabled = getIsLinkDisabled(step);

    return {
      label: step.label ?? "",
      completed,
      current: current,
      disabled,
      onClick: _handleLinkClick,
    };
  }),
);
</script>

<template>
  <FormStepperBase :data="data" />
</template>
