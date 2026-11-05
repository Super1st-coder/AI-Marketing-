<script setup lang="ts">
import { SelectOption } from "../forms/base/FieldBaseSelect.vue";
import { MetricData, MetricGroup } from "@/services/UtilsApi";
import { CampaignFormChannelGroupMetric } from "./CampaignFormMetricsModal.vue";

const props = defineProps<{
  metricGroupName: MetricGroup;
  name: string;
  predefinedMetrics: MetricData[];
  usedPredefinedNames?: string[];
}>();

const emit = defineEmits<{
  delete: [];
}>();

const { t } = useI18n();

const { value: model } = useField<CampaignFormChannelGroupMetric>(
  () => props.name,
);

const options = computed<SelectOption[]>(() => {
  const reserved = props.usedPredefinedNames ?? [];

  const all =
    props.predefinedMetrics
      .filter(
        (predefinedMetric) => predefinedMetric.group === props.metricGroupName,
      )
      .filter((predefinedMetric) =>
        // Filter out the used predefined metrics
        model.value.goal_type === "not_defined"
          ? !reserved.includes(predefinedMetric.name)
          : model.value.name === predefinedMetric.name
            ? true
            : !reserved.includes(predefinedMetric.name),
      )
      .map((metric) => ({
        label: t(
          `campaigns.metric-groups.metrics.${metric.name}.display_name`,
          metric.display_name,
        ),
        value: metric.name,
      })) ?? [];

  return [
    { label: t("campaigns.metric-groups.global.custom"), value: "custom" },
    ...all,
  ];
});

const unitOptions = computed<SelectOption[]>(() => {
  return [
    { label: "-", value: null },
    { label: "%", value: "%" },
    { label: "$", value: "$" },
  ];
});

const goalModel = computed<string | undefined>({
  get: () => {
    if (model.value.goal_type === "custom") return "custom";
    if (model.value.goal_type === "not_defined") return undefined;
    return model.value.name;
  },
  set: (val) => {
    if (val === "custom") {
      model.value = {
        goal_type: "custom",
        display_name: "",
        name: "",
        unit: null,
        type: "number",
        value: undefined,
        target: "",
        group: props.metricGroupName,
      };
    } else {
      const metric = props.predefinedMetrics.find(
        (metric) => metric.name === val,
      );
      if (!metric) return;

      model.value = {
        goal_type: "predefined",
        display_name: metric.display_name,
        name: metric.name,
        unit: metric.unit,
        type: "number",
        value: undefined,
        target: metric.target,
        group: props.metricGroupName,
      };
    }
  },
});
</script>

<template>
  <div class="tw:flex tw:items-start tw:justify-between">
    <div
      class="tw:flex tw:grow tw:flex-col tw:items-start tw:gap-1 tw:lg:flex-row tw:lg:gap-4"
    >
      <template
        v-if="
          model.goal_type === 'not_defined' || model.goal_type === 'predefined'
        "
      >
        <FieldBaseNewSelect
          :name="`${name}.goal_type`"
          :options="options"
          class="tw:shrink-0 tw:lg:basis-[250px]"
          :placeholder="
            $t(
              `campaigns.metric-groups.${metricGroupName}.modal.select-placeholder`,
            )
          "
          :clearable="false"
          v-model="goalModel"
        />
      </template>

      <template v-if="model.goal_type === 'custom'">
        <FieldText
          :name="`${name}.display_name`"
          class="tw:shrink-0 tw:lg:basis-[250px]"
          :placeholder="
            $t(
              `campaigns.metric-groups.${metricGroupName}.modal.custom-name-placeholder`,
            )
          "
        />
      </template>

      <template
        v-if="model.goal_type === 'custom' || model.goal_type === 'predefined'"
      >
        <div class="tw:flex tw:w-full tw:gap-2 tw:lg:w-auto">
          <FieldMoney
            v-if="model.unit === '$'"
            :name="`${name}.value`"
            class="tw:grow tw:lg:shrink-0 tw:lg:grow-0 tw:lg:basis-[150px]"
            :placeholder="
              $t('campaigns.metric-groups.global.value-placeholder')
            "
            currency="USD"
          />
          <FieldNumber
            v-else
            :name="`${name}.value`"
            class="tw:grow tw:lg:shrink-0 tw:lg:grow-0 tw:lg:basis-[150px]"
            :placeholder="
              $t('campaigns.metric-groups.global.value-placeholder')
            "
            :digits="20"
          />

          <FieldAutocomplete
            :name="`${name}.unit`"
            :options="unitOptions"
            class="tw:basis-[150px] tw:lg:shrink-0 tw:lg:basis-[100px]"
            :disabled="model.goal_type === 'predefined'"
          />
        </div>
      </template>

      <template v-if="model.goal_type === 'custom'">
        <FieldText
          :name="`${name}.target`"
          class="tw:lg:basis-[280px]"
          :placeholder="$t('campaigns.metric-groups.global.target-placeholder')"
        />
      </template>

      <template v-if="model.goal_type === 'predefined'">
        <p class="tw:pt-2">
          {{
            t(
              `campaigns.metric-groups.metrics.${model.name}.target`,
              model.target,
            )
          }}
        </p>
      </template>
    </div>

    <button type="button" class="tw:py-4 tw:pl-4" @click="emit('delete')">
      <Icon icon="tabler-x" class="tw:text-base" />
    </button>
  </div>
</template>
