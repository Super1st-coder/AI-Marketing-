<script setup lang="ts">
interface Props {
  progress?: number;
  diameter?: number;
  thickness?: number;
  gradient?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  progress: 0,
  diameter: 180,
  thickness: 12,
  gradient: false,
});

const center = computed(() => props.diameter / 2);
const radius = computed(() => (props.diameter - props.thickness) / 2);
const gradientId = useId();

const stroke = computed(() =>
  props.gradient ? `url(#${gradientId})` : "currentColor",
);
</script>

<template>
  <svg
    :width="diameter"
    :height="diameter"
    :viewBox="`0 0 ${diameter} ${diameter}`"
    style="stroke-linecap: round"
  >
    <defs v-if="gradient">
      <!-- Primary/100 → Primary/500 -->
      <linearGradient
        :id="gradientId"
        :x1="diameter"
        y1="0"
        x2="0"
        :y2="diameter"
        gradientUnits="userSpaceOnUse"
      >
        <stop offset="0%" stop-color="#FFE7CF" />
        <stop offset="100%" stop-color="#FF8811" />
      </linearGradient>
    </defs>

    <circle
      class="percent"
      :cx="center"
      :cy="center"
      :r="radius"
      fill="none"
      :stroke="stroke"
      :stroke-width="thickness"
      pathLength="100"
      stroke-dasharray="100"
      :style="{ strokeDashoffset: 100 - progress * 100 }"
    />
  </svg>
</template>
