<script setup lang="ts">
import { computed } from "vue";
import { type FormStepperStep } from "@/components/forms/multi-step/FormStepperBase.vue";
import { useMultiStepFormContext } from "@/composables/multi-step-form/useMultiStepContext";
import type { FormStep } from "@/composables/multi-step-form/useMultiStepForm";

const { flattenSteps, handleLinkClick, getIsLinkCompleted, getIsLinkSelected } =
  useMultiStepFormContext();

const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

// The pre-check is reachable once a configuration has been submitted, or when
// a published campaign has been loaded from the publish endpoint
const isConfigurationCompleted = computed(
  () => preCheckStore.preCheckResponse !== undefined,
);

const steps = computed<{ name: string; label: string; disabled: boolean }[]>(
  () => [
    { name: "launchpadTutorial", label: "Context", disabled: false },
    {
      name: "launchpadTechnicalConfig",
      label: "Configuration",
      disabled: false,
    },
    {
      name: "launchpadPreCheck",
      label: "Pre-check",
      disabled: !isConfigurationCompleted.value,
    },
    {
      name: "launchpadSummary",
      label: "Summary",
      // Only a published campaign has a summary: running the pre-check again
      // disables it until the campaign is published
      disabled: !preCheckStore.isPublished,
    },
  ],
);

const data = computed<FormStepperStep[]>(() => {
  return steps.value.map(({ name, label, disabled }) => {
    const flatStep = flattenSteps.value.find((s: FormStep) => s.name === name);
    if (!flatStep) {
      return { label, completed: false, current: false, disabled: true };
    }

    return {
      label,
      completed: getIsLinkCompleted(flatStep),
      current: getIsLinkSelected(flatStep),
      disabled,
      onClick: () => handleLinkClick(flatStep),
    };
  });
});
</script>

<template>
  <FormStepperBase :data="data" />
</template>
