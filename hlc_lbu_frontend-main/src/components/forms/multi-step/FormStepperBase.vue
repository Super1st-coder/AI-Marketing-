<script setup lang="ts">
export interface FormStepperStep {
  label: string;
  completed?: boolean;
  current?: boolean;
  disabled?: boolean;
  onClick?: Function;
}

withDefaults(
  defineProps<{
    data: FormStepperStep[];
  }>(),
  {
    data: () => [],
  },
);
</script>

<template>
  <ul class="tw:flex tw:w-full tw:flex-wrap tw:items-center tw:gap-3">
    <template v-for="(step, index) in data" :key="step.label">
      <li
        class="tw:flex tw:items-center tw:gap-3"
        :class="{ 'tw:opacity-50': step.disabled }"
      >
        <!-- Step indicator: Icon + Label -->
        <div class="tw:flex tw:shrink-0 tw:items-center tw:gap-2">
          <Icon
            :icon="
              step.completed
                ? 'tabler:circle-check-filled'
                : step.current
                  ? 'ix-circle-dot-filled'
                  : 'ic-outline-circle'
            "
            class="tw:shrink-0 tw:text-[16px]"
            :class="
              step.completed
                ? 'tw:text-primary'
                : step.current
                  ? 'tw:text-primary'
                  : 'tw:text-gray-300'
            "
          />

          <button
            class="tw:block tw:text-xs tw:font-medium tw:whitespace-nowrap"
            :class="{
              'tw:text-secondary-text': !step.current,
              'tw:cursor-not-allowed!': step.disabled,
            }"
            type="button"
            @click="step.onClick?.()"
            :disabled="step.disabled"
          >
            {{ step.label }}
          </button>
        </div>

        <!-- Chevron separator (not on last item) -->
        <Icon
          v-if="index !== data.length - 1"
          icon="tabler-chevron-compact-right"
          class="tw:text-xl tw:text-gray-300"
        />
      </li>
    </template>
  </ul>
</template>
