<script setup lang="ts">
import type { ButtonProps } from "@/components/buttons/base/Button.vue";

export type LucaGuideTimeframe =
  | { type: "days"; days: number }
  | { type: "max" }
  | { type: "custom"; startDate: string; days: number }
  | { type: "custom-range"; startDate: string; endDate: string };

export type LucaGuideTimeFilterOption =
  number | "max" | "custom" | "custom-range";

const model = defineModel<LucaGuideTimeframe>({ required: true });

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    options: LucaGuideTimeFilterOption[];
    size?: ButtonProps["size"];
    // Data-sync gating (Jake): while the post-connect daily backfill is still running, only
    // windows covered by the days loaded so far are meaningful. `availableDays` is the distinct
    // days loaded; when `syncing` is true we disable presets (and "max") that reach past it, and
    // floor the custom-range picker at `minDate`. Once syncing finishes, everything re-enables.
    syncing?: boolean;
    availableDays?: number;
    minDate?: string;
  }>(),
  { size: "sm" },
);

// A preset/"max" reaches past what's loaded and should be gated — but only while syncing, and
// only once we actually know the coverage (availableDays defined). Not-yet-loaded ⇒ don't gate.
function isGated(neededDays: number | "max") {
  if (!props.syncing || props.availableDays == null) {
    return false;
  }
  if (neededDays === "max") {
    return true; // full history is never fully loaded until the sync completes
  }
  return neededDays > props.availableDays;
}

function isDaysSelected(days: number) {
  return model.value.type === "days" && model.value.days === days;
}

function isSelected(type: LucaGuideTimeframe["type"]) {
  return model.value.type === type;
}

function selectDays(days: number) {
  if (isDaysSelected(days)) {
    return;
  }

  model.value = { type: "days", days };
}

function selectMax() {
  if (isSelected("max")) {
    return;
  }

  model.value = { type: "max" };
}

function selectCustom(value: { startDate: string; days: number }) {
  model.value = {
    type: "custom",
    startDate: value.startDate,
    days: value.days,
  };
}

function selectCustomRange(value: { startDate: string; endDate: string }) {
  if (
    model.value.type === "custom-range" &&
    model.value.startDate === value.startDate &&
    model.value.endDate === value.endDate
  ) {
    return;
  }

  model.value = {
    type: "custom-range",
    startDate: value.startDate,
    endDate: value.endDate,
  };
}
</script>

<template>
  <div
    class="tw:flex tw:flex-wrap tw:gap-2"
    role="group"
    :aria-label="$t('luca-guide.timeframe.label')"
  >
    <template v-for="option in options" :key="option">
      <Button
        v-if="typeof option === 'number'"
        type="button"
        :size="size"
        :shadow="false"
        :disabled="disabled || isGated(option)"
        :title="
          isGated(option) ? $t('luca-guide.timeframe.gated-hint') : undefined
        "
        :variant="isDaysSelected(option) ? 'label' : 'outlined'"
        :color="isDaysSelected(option) ? 'primary' : 'secondary'"
        :aria-pressed="isDaysSelected(option)"
        @click="selectDays(option)"
      >
        {{ $t("luca-guide.timeframe.last-days", { days: option }) }}
      </Button>

      <Button
        v-if="option === 'max'"
        type="button"
        :size="size"
        leftIcon="tabler:infinity"
        :shadow="false"
        :disabled="disabled || isGated('max')"
        :title="
          isGated('max') ? $t('luca-guide.timeframe.gated-hint') : undefined
        "
        :variant="isSelected('max') ? 'label' : 'outlined'"
        :color="isSelected('max') ? 'primary' : 'secondary'"
        :aria-pressed="isSelected('max')"
        @click="selectMax"
      >
        {{ $t("luca-guide.timeframe.max") }}
      </Button>

      <LucaGuideCustomDateButton
        v-if="option === 'custom'"
        :active="isSelected('custom')"
        :disabled="disabled"
        :size="size"
        :startDate="model.type === 'custom' ? model.startDate : undefined"
        @select="selectCustom"
      />

      <LucaGuideCustomRangeButton
        v-if="option === 'custom-range'"
        :active="isSelected('custom-range')"
        :disabled="disabled"
        :size="size"
        :startDate="model.type === 'custom-range' ? model.startDate : undefined"
        :endDate="model.type === 'custom-range' ? model.endDate : undefined"
        :minDate="syncing ? minDate : undefined"
        @select="selectCustomRange"
      />
    </template>
  </div>
</template>
