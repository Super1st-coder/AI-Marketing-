<script lang="ts" setup>
export type WizardStep = string;

export interface WizardStage {
  key: string;
  label: string;
  steps: WizardStep[];
}

interface Props {
  stages: WizardStage[];
  currentStep: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  clickStage: [stage: WizardStage];
}>();

const stages = toRef(props, "stages");
const currentStep = toRef(props, "currentStep");
const { currentStageIndex } = useWizardStagesHelper(stages, currentStep);

const isLastStage = (stageIndex: number) => {
  return stageIndex === props.stages.length - 1;
};

const getIcon = (index: number) => {
  if (index < currentStageIndex.value) {
    return "tabler-circle-check-filled";
  } else {
    return "tabler-circle";
  }
};

const isStageDisabled = (index: number) => {
  return index > currentStageIndex.value;
};

const isButtonHiddenInMobile = (index: number) => {
  if (currentStageIndex.value === 0) {
    return index > 2;
  } else if (currentStageIndex.value === props.stages.length - 1) {
    return index < currentStageIndex.value - 2;
  } else {
    return (
      index < currentStageIndex.value - 1 || index > currentStageIndex.value + 1
    );
  }
};

const isBarHiddenInMobile = (index: number) => {
  if (currentStageIndex.value === 0) {
    return index > 1;
  } else if (currentStageIndex.value === props.stages.length - 1) {
    return index < currentStageIndex.value - 2;
  } else {
    return (
      index < currentStageIndex.value - 1 || index > currentStageIndex.value
    );
  }
};

const clickStage = (stage: WizardStage) => {
  emit("clickStage", stage);
};
</script>

<template>
  <div class="tw:flex tw:gap-2">
    <template v-for="(stage, stageIndex) in stages" :key="stage.key">
      <button
        :disabled="isStageDisabled(stageIndex)"
        class="tw:flex tw:grow tw:basis-0 tw:flex-col tw:items-center tw:gap-4 tw:lg:grow-0 tw:lg:basis-auto"
        :class="{
          'tw:hidden tw:lg:flex': isButtonHiddenInMobile(stageIndex),
        }"
        @click="clickStage(stage)"
      >
        <Icon
          :icon="getIcon(stageIndex)"
          class="tw:inline-block tw:text-[20px] tw:text-primary"
          :class="{ 'tw:opacity-15': isStageDisabled(stageIndex) }"
        />
        <span>{{ stage.label }}</span>
      </button>

      <div
        v-if="!isLastStage(stageIndex)"
        class="tw:mt-2.5 tw:h-[3px] tw:min-w-4 tw:grow-[0.25] tw:basis-0 tw:rounded tw:bg-primary tw:sm:grow-[0.5] tw:lg:grow"
        :class="{
          'tw:opacity-15': stageIndex > currentStageIndex - 1,
          'tw:hidden tw:lg:block': isBarHiddenInMobile(stageIndex),
        }"
      ></div>
    </template>
  </div>
</template>
