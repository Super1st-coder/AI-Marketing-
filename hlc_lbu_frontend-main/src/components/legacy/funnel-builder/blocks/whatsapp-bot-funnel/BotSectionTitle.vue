<script lang="ts" setup>
interface Props {
  viewSimulation?: string;
}

defineProps<Props>();

const emit = defineEmits<{
  (e: "viewSimulation"): void;
}>();

const hasViewSimulationListener = computed(
  () => !!getCurrentInstance()?.vnode.props?.onViewSimulation,
);
</script>

<template>
  <div
    :class="{
      'tw:flex tw:items-center tw:justify-between tw:gap-4':
        hasViewSimulationListener,
    }"
  >
    <h2 class="tw:text-xl tw:font-extrabold">
      <slot />
    </h2>

    <button
      v-if="hasViewSimulationListener"
      @click="emit('viewSimulation')"
      class="tw:text-lg tw:font-medium tw:text-primary tw:underline"
      type="button"
    >
      View Simulation
    </button>
  </div>
</template>
