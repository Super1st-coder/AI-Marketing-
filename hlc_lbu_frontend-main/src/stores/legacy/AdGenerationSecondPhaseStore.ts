import { WizardStage } from "@/components/legacy/wizard-form/WizardSteps.vue";
import { defineStore } from "pinia";

export const useAdGenerationSecondPhaseStore = defineStore(
  "AdGenerationSecondPhaseStore",
  () => {
    const { t } = useI18n();

    const stages = computed<WizardStage[]>(() => [
      {
        key: "targetBuyer",
        label: t("process.steps.target-buyer"),
        steps: ["targetBuyer"],
      },
      {
        key: "product",
        label: t("process.steps.product"),
        steps: ["product"],
      },
      {
        key: "yourHypothesis",
        label: t("process.steps.your-hypothesis"),
        steps: ["yourHypothesis"],
      },
    ]);

    const wizard = useWizardState(stages);

    return {
      ...wizard,
    };
  },
);
