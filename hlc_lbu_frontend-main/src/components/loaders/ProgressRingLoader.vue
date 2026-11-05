<script lang="ts" setup>
import { useIntervalFn } from "@vueuse/core";
import { computed, ref, watch } from "vue";

interface Props {
  steps: string[];
  completed?: boolean;
  interval?: number;
}

const props = withDefaults(defineProps<Props>(), { interval: 2000 });

const currentStepIndex = ref(-1);
const maxInProgressStepIndex = computed(() =>
  Math.max(props.steps.length - 1, 0),
);

// Increase the current step using an interval
useIntervalFn(
  () => {
    if (props.completed) {
      return;
    }

    currentStepIndex.value = Math.min(
      currentStepIndex.value + 1,
      maxInProgressStepIndex.value,
    );
  },
  () => props.interval,
  { immediate: true },
);

// Keep current index inside the steps if they are changed
watch(
  () => props.steps.length,
  () => {
    currentStepIndex.value = Math.min(
      currentStepIndex.value,
      maxInProgressStepIndex.value,
    );
  },
);

const percentage = computed(() => {
  if (props.completed) {
    return 100;
  }

  return ((currentStepIndex.value + 1) / (props.steps.length + 1)) * 100;
});

const isStepCompleted = (stepIndex: number) => {
  if (props.completed) {
    return true;
  }

  return stepIndex < currentStepIndex.value;
};

const isStepCurrent = (stepIndex: number) =>
  currentStepIndex.value === stepIndex;

function getStepStatus(index: number) {
  return isStepCompleted(index)
    ? "completed"
    : isStepCurrent(index)
      ? "current"
      : "pending";
}
</script>

<template>
  <div class="tw:flex tw:flex-col tw:items-center">
    <ProgressRing
      :progress="percentage / 100"
      :diameter="180"
      :thickness="12"
      gradient
      displayPercentage
    />

    <h2 class="tw:mb-3 tw:text-center tw:text-3xl tw:font-bold">
      <slot name="title" />
    </h2>

    <p class="tw:mb-6 tw:text-center tw:font-medium tw:text-secondary-text">
      <slot name="description" />
    </p>

    <ol
      class="tw:mx-auto tw:grid tw:w-full tw:grid-cols-1 tw:gap-3"
      style="max-width: 350px"
    >
      <li
        v-for="(step, index) in steps"
        class="tw:flex tw:items-center tw:gap-3"
      >
        <span class="tw:text-xl">
          <Icon
            v-show="getStepStatus(index) === 'completed'"
            icon="tabler:circle-check-filled"
            class="tw:text-success"
          />
          <Icon
            v-show="getStepStatus(index) === 'pending'"
            icon="ic-outline-circle"
            class="tw:text-secondary-text"
          />
          <Icon
            v-show="getStepStatus(index) === 'current'"
            icon="ix-circle-dot-filled"
            class="tw:text-primary"
          />
        </span>
        <span class="tw:font-medium tw:text-secondary-text">{{ step }}...</span>
      </li>
    </ol>
  </div>
</template>
