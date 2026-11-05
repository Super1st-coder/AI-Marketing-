<script setup lang="ts">
export type ProgressRingColor = "primary" | "success";

interface Props {
  progress: number;
  diameter?: number;
  thickness?: number;
  gradient?: boolean;
  displayPercentage?: boolean;
  color?: ProgressRingColor;
}

const props = withDefaults(defineProps<Props>(), {
  progress: 0,
  diameter: 180,
  thickness: 12,
  gradient: false,
  color: "primary",
});

const clampedProgress = computed(() =>
  Math.min(Math.max(props.progress, 0), 1),
);

const percentage = computed(() => clampedProgress.value * 100);

const useGradient = computed(() => props.gradient && props.color === "primary");
</script>

<template>
  <div
    class="progress-ring tw:relative tw:shrink-0"
    :style="{ width: `${diameter}px`, height: `${diameter}px` }"
  >
    <ProgressRingBase
      :class="{
        'tw:text-gray-300': color === 'success',
        'tw:text-primary tw:opacity-20': color === 'primary',
      }"
      :diameter="diameter"
      :thickness="thickness"
      :gradient="useGradient"
    />

    <ProgressRingBorder
      class="tw:absolute tw:top-1/2 tw:left-1/2 tw:-translate-x-1/2 tw:-translate-y-1/2"
      :class="{
        'tw:text-success-500': color === 'success',
        'tw:text-primary': color === 'primary',
      }"
      :progress="clampedProgress"
      :diameter="diameter"
      :thickness="thickness"
      :gradient="useGradient"
    />

    <span
      v-if="displayPercentage"
      class="tw:absolute tw:top-1/2 tw:left-1/2 tw:-translate-x-1/2 tw:-translate-y-1/2 tw:text-5xl tw:font-bold tw:wrap-normal"
      :class="{
        'tw:text-success-500': color === 'success',
        'tw:text-primary': color === 'primary',
      }"
    >
      {{ percentage }}%
    </span>
  </div>
</template>
