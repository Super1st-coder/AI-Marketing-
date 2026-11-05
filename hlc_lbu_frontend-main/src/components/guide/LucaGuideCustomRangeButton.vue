<script setup lang="ts">
import { VDateRangePicker } from "vuetify/labs/VDateRangePicker";
import type { ButtonProps } from "@/components/buttons/base/Button.vue";

const props = defineProps<{
  active?: boolean;
  disabled?: boolean;
  startDate?: string;
  endDate?: string;
  // Earliest selectable day — the first day of loaded daily data. While the account is still
  // syncing, days before this aren't downloaded yet, so the picker floor stops the user from
  // requesting an empty range (Jake).
  minDate?: string;
  size?: ButtonProps["size"];
}>();

const emit = defineEmits<{
  select: [value: { startDate: string; endDate: string }];
}>();

const { locale } = useI18n();

const today = computed(() => formatLocalIsoDate(new Date()));
const draftRange = ref<Date[]>([]);

const label = computed(() => {
  if (draftRange.value.length < 2) {
    return null;
  }

  const [start, end] = draftRange.value;

  return formatDateRange(start, end, locale.value);
});

const canApply = computed(() => draftRange.value.length >= 2);

watch(
  () => [props.startDate, props.endDate] as const,
  ([startDate, endDate]) => {
    if (!startDate || !endDate) {
      return;
    }

    draftRange.value = [
      parseLocalIsoDate(startDate),
      parseLocalIsoDate(endDate),
    ];
  },
  { immediate: true },
);

function applyRange(close: () => void) {
  if (draftRange.value.length < 2) {
    return;
  }

  const startDate = formatLocalIsoDate(draftRange.value[0]);
  const endDate = formatLocalIsoDate(
    draftRange.value[draftRange.value.length - 1],
  );
  const [start, end] =
    startDate <= endDate ? [startDate, endDate] : [endDate, startDate];

  emit("select", { startDate: start, endDate: end });
  close();
}
</script>

<template>
  <ButtonDropdown
    type="button"
    :size="size"
    leftIcon="tabler:calendar"
    placement="bottom-end"
    :shadow="false"
    :disabled="disabled"
    :variant="active ? 'label' : 'outlined'"
    :color="active ? 'primary' : 'secondary'"
    :aria-pressed="active"
  >
    {{ label ?? $t("luca-guide.timeframe.custom") }}

    <template #options="{ close }">
      <div class="luca-guide-custom-range-picker">
        <VDateRangePicker
          v-model="draftRange"
          hide-header
          hide-title
          independent-months
          color="primary"
          bg-color="transparent"
          weekday-format="narrow"
          :max="today"
          :min="minDate"
          :elevation="0"
        >
          <template #footer>
            <div class="tw:flex tw:w-full tw:justify-end">
              <Button
                type="button"
                size="sm"
                :disabled="!canApply"
                @click="applyRange(close)"
              >
                {{ $t("luca-guide.timeframe.update-date") }}
              </Button>
            </div>
          </template>
        </VDateRangePicker>
      </div>
    </template>
  </ButtonDropdown>
</template>

<style scoped>
.luca-guide-custom-range-picker :deep(.v-date-picker-month__range-bg) {
  background-color: rgb(var(--v-theme-primary));
}
</style>
