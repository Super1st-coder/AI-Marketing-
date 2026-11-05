import { WizardStage } from "@/components/legacy/wizard-form/WizardSteps.vue";
import { defineStore } from "pinia";

export const useAdGenerationFirstPhaseStore = defineStore(
  "AdGenerationFirstPhaseStore",
  () => {
    const { t } = useI18n();

    const stages = computed<WizardStage[]>(() => [
      {
        key: "hypothesis",
        label: t("process.steps.hypothesis"),
        steps: ["hypothesis"],
      },
      {
        key: "yourProduct",
        label: t("process.steps.your-product"),
        steps: ["yourProduct", "yourProductRefinement"],
      },
      {
        key: "yourTarget",
        label: t("process.steps.your-target"),
        steps: ["yourTarget", "yourTargetRefinement"],
      },
      {
        key: "element",
        label: t("process.steps.element"),
        steps: ["element", "elementRefinement"],
      },
      {
        key: "goal",
        label: t("process.steps.goal"),
        steps: ["goal", "goalRefinement"],
      },
      {
        key: "buyerChallenge",
        label: t("process.steps.buyer-challenge"),
        steps: ["buyerChallenge", "buyerChallengeRefinement"],
      },
    ]);

    const wizard = useWizardState(stages);

    return {
      ...wizard,
    };
  },
);
