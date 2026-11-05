<script setup lang="ts">
defineProps<{
  priorityLabel: string;
  kpiName: string;
  value: string;
  targetLabel: string;
  deltaLabel?: string;
  deltaOverTarget?: boolean;
  /** Value / delta tone relative to target. */
  tone?: "success" | "warning" | "error" | "secondary";
  highlighted?: boolean;
  /** Shown under a blank ("—") value to explain WHY it's empty. */
  reasonLabel?: string;
}>();
</script>

<template>
  <CardBase
    borderRadius="md"
    :outlineColor="highlighted ? 'primary' : 'default'"
    :borderWidth="highlighted ? 2 : 1"
    class="tw:flex tw:flex-col tw:items-center tw:gap-4 tw:p-4 tw:wrap-normal"
    :shadow="false"
  >
    <div
      class="tw:flex tw:items-start tw:justify-between tw:gap-2 tw:self-stretch tw:text-sm"
    >
      <p
        class="tw:font-bold"
        :class="{
          'tw:text-primary': highlighted,
        }"
      >
        {{ priorityLabel }}
      </p>

      <p class="tw:text-secondary-text">
        {{ kpiName }}
      </p>
    </div>

    <p
      class="tw:text-4xl tw:font-bold"
      :class="{
        'tw:text-success': tone === 'success',
        'tw:text-warning': tone === 'warning',
        'tw:text-error': tone === 'error',
        'tw:text-secondary-text': tone === 'secondary' || !tone,
      }"
    >
      {{ value }}
    </p>

    <p
      v-if="reasonLabel"
      class="tw:-mt-2 tw:text-center tw:text-xs tw:text-secondary-text"
    >
      {{ reasonLabel }}
    </p>

    <p
      class="tw:flex tw:flex-wrap tw:items-center tw:justify-center tw:gap-3 tw:text-sm"
    >
      <span class="tw:text-gray-400">{{ targetLabel }}</span>

      <span
        v-if="deltaLabel"
        class="tw:flex tw:items-center tw:gap-0.5 tw:font-semibold"
        :class="{
          'tw:text-success': tone === 'success',
          'tw:text-warning': tone === 'warning',
          'tw:text-error': tone === 'error',
          'tw:text-secondary-text': tone === 'secondary' || !tone,
        }"
      >
        <Icon
          :icon="deltaOverTarget ? 'tabler:arrow-up' : 'tabler:arrow-down'"
          class="tw:text-[16px]"
        />

        <span>{{ deltaLabel }}</span>
      </span>
    </p>
  </CardBase>
</template>
