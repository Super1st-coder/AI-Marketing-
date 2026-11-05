<script setup lang="ts">
import { object } from "yup";
import UtilsApi, { MetricGroup } from "@/services/UtilsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { CampaignFormData } from "./CampaignForm.vue";
import CampaignsApi, {
  CampaignChannelGroupMetric,
} from "@/services/projects/CampaignsApi";
import { MetricsChannelGroup } from "@/components/metrics/types";

const brandId = useBrandId();
const projectId = useProjectId();

const { data: predefinedMetrics } = await UtilsApi.getMetricList();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<CampaignFormData>();

const schema = computed(() => toTypedSchema(object({})));

const channelGroups = ref(
  (data.value.channel_group?.map((channelGroup) => ({
    id: channelGroup.id,
    name: channelGroup.name,
    groups: {
      Goals:
        channelGroup.metrics?.filter(
          (metric) => metric && metric.group === "Goals",
        ) ?? [],
      Resources:
        channelGroup.metrics?.filter(
          (metric) => metric && metric.group === "Resources",
        ) ?? [],
      Marketing:
        channelGroup.metrics?.filter(
          (metric) => metric && metric.group === "Marketing",
        ) ?? [],
    },
  })) ?? []) satisfies MetricsChannelGroup[],
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {},
  keepValuesOnUnmount: true,
});

const saveAllMetrics = async (advance: boolean) => {
  const metricsData = channelGroups.value.map((channelGroup) => ({
    channel_group: channelGroup.id,
    metrics: Object.values(
      channelGroup.groups,
    ).flatMap<CampaignChannelGroupMetric>((metrics) => metrics),
  }));

  let response = await CampaignsApi.setMetrics(
    brandId,
    projectId,
    data.value.id,
    { channel_group_metrics: metricsData, advance },
  );

  // Save data and go next
  saveData({
    ...response.data,
    // The response doesn't come with "channel_group", it's called "channel_group_metrics" and
    // it only includes "channel_group" and "metrics" in its data
    channel_group: data.value.channel_group!.map((group) => ({
      ...group,
      // Get the metrics for this group in the response
      metrics: response.data.channel_group_metrics.find(
        (_group) => _group.channel_group === group.id,
      )?.metrics,
    })),
  });

  return metricsData;
};

const { confirm } = useConfirmModal();

const onSubmit = handleSubmit(async (_values) => {
  const hadInitialMetrics = data.value.channel_group?.some((group) =>
    group.metrics ? group.metrics?.length > 0 : false,
  );

  // Wait for the confirm modal
  if (
    !hasOneKpiEverywhere.value ||
    (hasOneKpiEverywhere.value && !hadInitialMetrics)
  ) {
    const answer = await confirm();
    if (answer !== "continue") {
      return;
    }
  }

  // Save and go next
  await saveAllMetrics(true);
  goNext();
});

const handleSave = async (
  groupIndex: number,
  groupName: MetricGroup,
  values: CampaignChannelGroupMetric[],
) => {
  // Save the metrics
  channelGroups.value[groupIndex].groups[groupName] = values;

  // Send to back-end
  await saveAllMetrics(false);
};

const isMetricsModalOpen = ref(false);
const activeMetricsModal = ref<
  | {
      groupIndex: number;
      metricGroupName: MetricGroup;
    }
  | undefined
>(undefined);

const activeChannelGroup = computed(() => {
  if (activeMetricsModal.value === undefined) return undefined;
  return channelGroups.value[activeMetricsModal.value.groupIndex];
});

const openMetricsModal = (groupIndex: number, metricGroupName: MetricGroup) => {
  activeMetricsModal.value = { groupIndex, metricGroupName };
  isMetricsModalOpen.value = true;
};

const handleModalSave = (
  metricGroupName: MetricGroup,
  values: CampaignChannelGroupMetric[],
) => {
  if (activeMetricsModal.value === undefined) return;
  return handleSave(
    activeMetricsModal.value.groupIndex,
    metricGroupName,
    values,
  );
};

const hasOneKpiEverywhere = computed(() =>
  // Check if in every one of the channel groups,
  channelGroups.value.every((group) =>
    // and in every one of their groups (Goals, Resources, Marketing),
    Object.values(group.groups).every(
      (group) =>
        // there's at least one
        group.length > 0,
    ),
  ),
);
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="kpis" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=21WcOjHaT-M"
    >
      {{ $t("campaigns.metrics.title") }}
      <template #description>
        {{ $t("campaigns.metrics.description") }}
      </template>
    </PageTitle>

    <MetricsMatrix :channelGroups="channelGroups">
      <template #action="{ index, metricGroupName }">
        <Button
          leftIcon="tabler-plus"
          size="xs"
          variant="label"
          type="button"
          @click="openMetricsModal(index, metricGroupName)"
        >
          {{
            $t(`campaigns.metric-groups.${metricGroupName}.modal.button-text`)
          }}
        </Button>
      </template>
    </MetricsMatrix>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <CampaignFormMetricsModal
      v-if="isMetricsModalOpen && activeMetricsModal && activeChannelGroup"
      v-model="isMetricsModalOpen"
      :channelName="activeChannelGroup.name"
      :metricGroupName="activeMetricsModal.metricGroupName"
      :initialMetrics="
        activeChannelGroup.groups[activeMetricsModal.metricGroupName]
      "
      :predefinedMetrics="predefinedMetrics"
      @save="handleModalSave"
    />

    <ModalFormSaveAlert :isDirty="meta.dirty" />

    <ModalConfirmGeneric
      :imageSrc="
        hasOneKpiEverywhere
          ? '/images/emojis/emoji-collision.png'
          : '/images/emojis/emoji-alarm-clock.png'
      "
    >
      <template #title>
        <template v-if="hasOneKpiEverywhere">
          Daaaamn! <br />
          {{ $t("campaigns.metrics.modalConfirm.titleone") }}
        </template>
        <template v-else>
          {{ $t("campaigns.metrics.modalConfirm.titletwo") }}
        </template>
      </template>

      <template #description>
        <template v-if="hasOneKpiEverywhere">
          {{ $t("campaigns.metrics.modalConfirm.descriptionone") }}
        </template>
        <template v-else>
          {{ $t("campaigns.metrics.modalConfirm.descriptiontwo") }}
          <br /><br />
          {{ $t("campaigns.metrics.modalConfirm.descriptionthree") }}
        </template>
      </template>

      <template #cancel>
        <template v-if="hasOneKpiEverywhere">
          {{ $t("global.back") }}
        </template>
        <template v-else>
          {{ $t("campaigns.metrics.modalConfirm.cancelsectiontexttwo") }}
        </template>
      </template>

      <template #continue>
        <template v-if="hasOneKpiEverywhere">
          {{ $t("campaigns.metrics.modalConfirm.continuessectionone") }}
        </template>
        <template v-else>
          {{ $t("campaigns.metrics.modalConfirm.continuessectiontwo") }}
        </template>
      </template>
    </ModalConfirmGeneric>
  </FormStepLayout>
</template>
