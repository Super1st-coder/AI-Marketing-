import { WizardStage } from "@/components/legacy/wizard-form/WizardSteps.vue";
import { defineStore } from "pinia";

export const useAdGenerationThirdPhaseStore = defineStore(
  "AdGenerationThirdPhaseStore",
  () => {
    const stages = computed<WizardStage[]>(() => [
      {
        key: "audience",
        label: "Audience",
        steps: ["audience"],
      },
      {
        key: "creativeConcept",
        label: "Creative concept",
        steps: [
          "creativeConceptIntro",
          "creativeConceptDetails",
          "creativeConceptRefinement",
          "creativeConcept",
          "campaignConcept",
        ],
      },
      {
        key: "funnelBuilder",
        label: "Marketing Funnel Builder",
        steps: [
          "funnelBuilderIntro1",
          "funnelBuilderIntro2",
          "chooseFunnelFramework",
        ],
      },
    ]);

    const wizard = useWizardState(stages);

    return {
      ...wizard,
    };
  },
);
