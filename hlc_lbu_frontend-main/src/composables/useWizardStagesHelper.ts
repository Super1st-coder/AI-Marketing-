export type WizardStep = string;

export interface WizardStage {
  key: string;
  label: string;
  steps: WizardStep[];
}

export function useWizardState(stages: Ref<WizardStage[]>) {
  const currentStep = ref<WizardStep>(stages.value[0].steps[0]);

  const { previousStep, nextStep, flattenSteps } = useWizardStagesHelper(
    stages,
    currentStep,
  );

  const goToNextStep = async () => {
    if (nextStep.value) {
      currentStep.value = nextStep.value;
      window.scrollTo(0, 0);
    }
  };

  const goToPreviousStep = () => {
    if (previousStep.value) {
      currentStep.value = previousStep.value;
      window.scrollTo(0, 0);
    }
  };

  const goToStage = (stage: WizardStage) => {
    // Go to the first step of the stage
    currentStep.value = stage.steps[0];
  };

  const goToLastStage = () => {
    const stage = stages.value[stages.value.length - 1];
    currentStep.value = stage.steps[stage.steps.length - 1];
  };

  return {
    stages,
    currentStep,
    previousStep,
    nextStep,
    flattenSteps,
    goToNextStep,
    goToPreviousStep,
    goToStage,
    goToLastStage,
  };
}

export function useWizardStagesHelper(
  stages: Ref<WizardStage[]>,
  currentStep: Ref<string>,
) {
  const stageOfCurrentStep = computed(
    () =>
      stages.value.find((stage) =>
        stage.steps.find((step) => step == currentStep.value),
      ) ?? stages.value[0],
  );

  const flattenSteps = computed(() =>
    stages.value.map((stage) => stage.steps).flat(),
  );

  const getStageIndex = (stage: WizardStage) =>
    stages.value.findIndex((item) => item.key === stage.key);

  const currentStageIndex = computed(() =>
    getStageIndex(stageOfCurrentStep.value),
  );

  const currentStepFlatIndex = computed(() =>
    flattenSteps.value.indexOf(currentStep.value),
  );

  const previousStep = computed(() => {
    const currentIndex = currentStepFlatIndex.value;
    if (currentIndex > 0) {
      return flattenSteps.value[currentIndex - 1];
    }

    return null;
  });

  const nextStep = computed(() => {
    const currentIndex = currentStepFlatIndex.value;
    if (currentIndex < flattenSteps.value.length) {
      return flattenSteps.value[currentIndex + 1];
    }

    return null;
  });

  return {
    stageOfCurrentStep,
    flattenSteps,
    getStageIndex,
    currentStageIndex,
    currentStepFlatIndex,
    previousStep,
    nextStep,
  };
}
