<script setup lang="ts">
import { VDatePicker } from "vuetify/components";
import type { ButtonProps } from "@/components/buttons/base/Button.vue";

const props = defineProps<{
  active?: boolean;
  disabled?: boolean;
  startDate?: string;
  size?: ButtonProps["size"];
}>();

const emit = defineEmits<{
  select: [value: { startDate: string; days: number }];
}>();

const { locale } = useI18n();

const today = computed(() => formatLocalIsoDate(new Date()));
const draftDate = ref<Date | null>(
  props.startDate ? parseLocalIsoDate(props.startDate) : null,
);

const label = computed(() => {
  if (!props.startDate) {
    return null;
  }

  return getDateRangeFormatter(locale.value).format(
    parseLocalIsoDate(props.startDate),
  );
});

watch(
  () => props.startDate,
  (startDate) => {
    if (!startDate) {
      return;
    }

    draftDate.value = parseLocalIsoDate(startDate);
  },
);

function daysFromStartDate(startDate: string) {
  const start = parseLocalIsoDate(startDate);
  const end = new Date();
  end.setHours(0, 0, 0, 0);

  const diffMs = end.getTime() - start.getTime();
  return Math.max(1, Math.round(diffMs / 86_400_000));
}

function onDateSelect(value: Date | null, close: () => void) {
  if (!value) {
    return;
  }

  const startDate = formatLocalIsoDate(value);
  emit("select", {
    startDate,
    days: daysFromStartDate(startDate),
  });
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
      <VDatePicker
        v-model="draftDate"
        hide-header
        hide-title
        color="primary"
        bg-color="transparent"
        weekday-format="narrow"
        :max="today"
        :elevation="0"
        @update:model-value="onDateSelect($event, close)"
      />
    </template>
  </ButtonDropdown>
</template>
