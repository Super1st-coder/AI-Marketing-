<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, lazy, number, object, string } from "yup";
import {
  MetricData,
  MetricGroup,
  MetricType,
  metricTypes,
} from "@/services/UtilsApi";
import { CampaignChannelGroupMetric } from "@/services/projects/CampaignsApi";

export type CampaignFormChannelGroupNotDefinedMetric = {
  goal_type: "not_defined";
};

export type CampaignFormChannelGroupPredefinedMetric = {
  goal_type: "predefined";
  name: string;
  display_name: string;
  unit: string | null;
  value: number;
  type: MetricType;
  target: string;
  group: MetricGroup;
};

export type CampaignFormChannelGroupCustomMetric = {
  goal_type: "predefined" | "custom";
  name: string;
  display_name: string;
  unit: string | null;
  value?: number;
  type: MetricType;
  target: string;
  group: MetricGroup;
};

export type CampaignFormChannelGroupMetric =
  | CampaignFormChannelGroupNotDefinedMetric
  | CampaignFormChannelGroupPredefinedMetric
  | CampaignFormChannelGroupCustomMetric;

const props = defineProps<{
  channelName: string;
  metricGroupName: MetricGroup;
  predefinedMetrics: MetricData[];
  initialMetrics: CampaignChannelGroupMetric[];
}>();

const emit = defineEmits<{
  save: [metricGroupName: MetricGroup, output: CampaignChannelGroupMetric[]];
}>();

const { t } = useI18n();

const isOpen = defineModel<boolean>({ required: true });

const notDefinedMetricSchema = computed(() =>
  object({
    goal_type: string().oneOf(["not_defined"]).required(),
  }),
);
const predefinedMetricSchema = computed(() =>
  object({
    goal_type: string().oneOf(["predefined"]).required(),
    name: string().required(),
    display_name: string().required(),
    unit: string().required().nullable(),
    value: number()
      .typeError(t("forms.must-be-number"))
      .notOneOf([0], t("forms.different-from", { number: 0 }))
      .required(),
    type: string().oneOf(metricTypes),
    target: string().required(),
    group: string().required(),
  }),
);
const customMetricSchema = computed(() =>
  object({
    goal_type: string().oneOf(["custom"]).required(),
    name: string(),
    display_name: string().required().trim(),
    unit: string().nullable(),
    value: number()
      .typeError(t("forms.must-be-number"))
      .notOneOf([0], t("forms.different-from", { number: 0 }))
      .required(),
    type: string().oneOf(metricTypes),
    target: string().required().trim(),
    group: string().required(),
  }),
);

const metricSchema = computed(() =>
  lazy((values) => {
    const { goal_type } = values;

    if (goal_type === "not_defined") {
      return notDefinedMetricSchema.value;
    }

    if (goal_type === "predefined") {
      return predefinedMetricSchema.value;
    }

    return customMetricSchema.value;
  }),
);

const schema = computed(() =>
  toTypedSchema(
    object({
      metrics: array().of(metricSchema.value).required(),
    }),
  ),
);

const { handleSubmit, values, isSubmitting, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      metrics: props.initialMetrics.map((metric) => {
        // Find a global metric that matches this one
        const predefinedMetric = props.predefinedMetrics.find(
          (predefinedMetric) =>
            predefinedMetric.group === props.metricGroupName &&
            predefinedMetric.name === metric.name,
        );

        // Set the predefined metric if it was found
        if (predefinedMetric) {
          return {
            name: predefinedMetric.name,
            display_name: predefinedMetric.display_name,
            type: predefinedMetric.type,
            unit: predefinedMetric.unit,
            target: predefinedMetric.target,
            group: predefinedMetric.group,
            value: castStringToNumber(metric.value),
            goal_type: "predefined" as const,
          };
        }

        return {
          ...metric,
          unit: metric.unit ?? null,
          display_name: metric.display_name ?? "Undefined",
          value: castStringToNumber(metric.value),
          target: metric.target ?? "Undefined",
          goal_type: "custom" as const,
        };
      }),
    },
    keepValuesOnUnmount: true,
  });

const onSubmit = handleSubmit(async (values) => {
  isOpen.value = false;

  const output = values.metrics
    .filter(
      (group) =>
        group.goal_type === "custom" || group.goal_type === "predefined",
    )
    .map<CampaignChannelGroupMetric>((metric) => {
      return {
        display_name: metric.display_name,
        name:
          metric.goal_type === "custom" && metric.display_name
            ? textToSnakeCase(metric.display_name)
            : metric.name,
        value: metric.value.toString(),
        unit: metric.unit,
        target: metric.target,
        type: metric.type,
        group: props.metricGroupName,
      };
    });

  emit("save", props.metricGroupName, output);
});

const handleAddGoal = () => {
  if (values.metrics) {
    setFieldValue("metrics", [...values.metrics, { goal_type: "not_defined" }]);
  }
};

const handleDelete = (indexToDelete: number) => {
  if (values.metrics) {
    setFieldValue(
      "metrics",
      values.metrics.filter((_item, index) => index !== indexToDelete),
    );
  }
};
</script>

<template>
  <Modal
    v-model="isOpen"
    class="tw:max-w-[1036px] tw:p-4 tw:lg:p-8"
    closeButton
    as="form"
    @submit.prevent="onSubmit"
  >
    <PageTitle
      helpButton
      is="h2"
      class="tw:mb-[38px]"
      helpVideoUrl="https://www.youtube.com/watch?v=21WcOjHaT-M"
    >
      {{
        $t(`campaigns.metric-groups.${metricGroupName}.modal.title`, {
          channelGroup: $t(`channel-groups.${channelName}.title`),
        })
      }}

      <template #description>
        {{ $t(`campaigns.metric-groups.${metricGroupName}.modal.description`) }}
      </template>
    </PageTitle>

    <template v-if="values.metrics && values.metrics.length > 0">
      <Separator class="tw:mb-6" />

      <div class="tw:mb-8 tw:flex tw:flex-col tw:gap-6">
        <CampaignFormMetricsModalItem
          v-for="(_metric, index) in values.metrics"
          :metricGroupName="metricGroupName"
          :name="`metrics[${index}]`"
          :predefinedMetrics="predefinedMetrics"
          :usedPredefinedNames="
            values.metrics
              .filter((metric) => metric.goal_type === 'predefined')
              .map((metric) => metric.name)
          "
          @delete="handleDelete(index)"
        />
      </div>

      <Separator class="tw:mb-6" />
    </template>

    <Button
      type="button"
      leftIcon="tabler-plus"
      variant="label"
      class="tw:mb-6 tw:w-full tw:lg:mb-[72px]"
      @click="handleAddGoal"
    >
      {{ $t(`campaigns.metric-groups.${metricGroupName}.modal.button-text`) }}
    </Button>

    <div class="tw:flex tw:justify-between tw:gap-2">
      <ButtonGoBack
        type="button"
        class="tw:basis-[260px]"
        @click="isOpen = false"
      >
        {{ $t("global.back") }}
      </ButtonGoBack>

      <Button class="tw:basis-[260px]" :isLoading="isSubmitting">
        {{ $t("global.save") }}
      </Button>
    </div>
  </Modal>
</template>
