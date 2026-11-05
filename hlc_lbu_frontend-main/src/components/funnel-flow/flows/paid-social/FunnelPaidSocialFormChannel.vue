<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object } from "yup";
import { FunnelPaidSocialFormData } from "./FunnelPaidSocialForm.vue";
import FunnelFlowApi from "@/services/funnel-flow/FunnelFlowApi";

const { goNext, data } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const brandId = useBrandId();
const campaignId = useCampaignId();
const paidSocialFormStore = useFunnelPaidSocialFormStore();

// Fetch and sort all the available channels

const { data: allChannelGroups } =
  await FunnelFlowApi.getChannelsByChannelGroup(data.value.channelGroupId);
const sortedChannelGroups = allChannelGroups.sort((a, b) =>
  a.active === b.active ? 0 : a.active ? -1 : 1,
);

// Fetch the selected channels in the flow
const { data: selectedChannels } = await FunnelFlowApi.getChannelsByFunnelFlow(
  brandId,
  campaignId,
  data.value.funnelFlowId,
);

// Create a reactive variable for the cards and checkboxes
const channelGroups = reactive(
  sortedChannelGroups.map((channel) => ({
    ...channel,
    selected:
      selectedChannels.channels.find(
        (channelB) => channel.id === channelB.id && channelB.active,
      ) !== undefined,
  })),
);

const activeChannelCount = computed(() =>
  channelGroups.reduce(function (acc, channel) {
    return acc + (channel.selected ? 1 : 0);
  }, 0),
);

const primaryChannel = computed(() =>
  channelGroups.find((channel) => channel.selected),
);

const schema = computed(() => toTypedSchema(object({})));

const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {},
});

const isSaving = ref(false);

const saveAllChannels = async () => {
  isSaving.value = true;

  // Save the selected channels
  await FunnelFlowApi.saveChannelsByFunnelFlow({
    brand_id: brandId,
    campaign_id: campaignId,
    funnel_flow_id: data.value.funnelFlowId,
    channels: channelGroups.map((group) => ({
      id: group.id,
      selected: group.selected,
    })),
  });

  // Revalidate funnel flow
  await paidSocialFormStore.revalidate();

  isSaving.value = false;
};

watch(
  () => channelGroups,
  async () => {
    await saveAllChannels();
  },
  { deep: true },
);

const onSubmit = handleSubmit(async (_values) => {
  // Next screen
  goNext();
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit">
    <!-- TODO: add help video URL later -->
    <PageTitle>
      {{ $t("funnel-flow.paid-social.channel.title") }}
    </PageTitle>

    <p class="tw:text-2xl tw:font-bold">
      {{ $t("funnel-flow.paid-social.channel.instruction") }}
    </p>

    <div
      class="tw:grid tw:grid-cols-2 tw:gap-5 tw:lg:grid-cols-3 tw:xl:grid-cols-4"
    >
      <FunnelPaidSocialFormChannelCard
        v-for="channelGroup in channelGroups"
        :channelGroup="channelGroup"
        :isSaving="isSaving"
        :activeChannelCount="activeChannelCount"
        :primaryChannel="primaryChannel"
        v-model="channelGroup.selected"
      />
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack
          :to="{ name: 'FunnelFlowHome', query: { view: 'funnelStages' } }"
        />

        <ButtonNext
          :disabled="activeChannelCount === 0 || isSaving"
          :isLoading="isSubmitting || isSaving"
        >
          {{ $t("funnel-flow.paid-social.channel.actions.next-structure") }}
        </ButtonNext>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
