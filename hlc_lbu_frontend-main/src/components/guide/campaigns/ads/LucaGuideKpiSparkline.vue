<script setup lang="ts">
import VueApexCharts from "vue3-apexcharts";

const props = withDefaults(
  defineProps<{
    data: number[];
    color: string;
    height?: number;
    formatValue?: (value: number) => string;
  }>(),
  {
    height: 60,
  },
);

const series = computed(() => {
  const points = props.data.length > 0 ? props.data : [0, 0];

  return [{ data: points }];
});

const chartOptions = computed<ApexCharts.ApexOptions>(() => ({
  chart: {
    type: "area",
    height: props.height,
    sparkline: { enabled: true },
    toolbar: { show: false },
    animations: { enabled: true },
  },
  markers: {
    size: 0,
    strokeWidth: 2,
    strokeColors: props.color,
    colors: ["#ffffff"],
    hover: {
      size: 5,
    },
  },
  stroke: {
    width: 2,
    curve: "smooth",
    colors: [props.color],
  },
  fill: {
    type: "gradient",
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.4,
      opacityTo: 0.1,
      gradientToColors: ["#ffffff"],
      stops: [0, 100],
    },
  },
  colors: [props.color],
  tooltip: {
    enabled: true,
    theme: "light",
    fixed: {
      enabled: true,
    },
    x: { show: false },
    y: {
      title: { formatter: () => "" },
      formatter: (value: number) => props.formatValue?.(value) ?? String(value),
    },
  },
}));
</script>

<template>
  <div class="tw:w-full">
    <VueApexCharts
      :key="color"
      type="area"
      :height="height"
      :options="chartOptions"
      :series="series"
    />
  </div>
</template>
