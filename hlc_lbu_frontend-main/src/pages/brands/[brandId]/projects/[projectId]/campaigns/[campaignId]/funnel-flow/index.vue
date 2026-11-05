<script lang="ts" setup>
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";
import CampaignsApi, {
  CampaignChannelGroupData,
} from "@/services/projects/CampaignsApi";
import { MetricGroup } from "@/services/UtilsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();
const campaign = (await CampaignsApi.getOne(brandId, projectId, campaignId))
  .data;

usePageTitle(() => t("routes.funnel-flow", { campaign: campaign.name }));

const route = useRoute();
const router = useRouter();

const allChannelsMetricsGroup = ref<CampaignChannelGroupData[] | undefined>();

const currentView = ref<"initial" | "funnelStages">(
  route.query.view === "funnelStages" ? "funnelStages" : "initial",
);

const {
  data: { channel_group: allChannelGroups },
} = await AdStructureApi.getChannelGroupList(brandId, campaignId);

if (
  shouldAutoRedirectFromFunnelFlowHome(allChannelGroups) &&
  route.query.view !== "funnelStages"
) {
  await router.replace({ name: "FunnelPaidSocial" });
}

const isNewFunnelModalOpen = ref<boolean>(false);

const isSingleChannelModalOpen = ref<boolean>(false);
const singleChannelModalGroup = ref<MetricGroup | undefined>();
const singleChannelModalMetricsGroup = ref<
  CampaignChannelGroupData | undefined
>();

const isAllChannelsModalOpen = ref<boolean>(false);
const allChannelsModalGroup = ref<MetricGroup | undefined>();

const openSingleChannelModal = (
  group: MetricGroup,
  metricsGroup: CampaignChannelGroupData,
) => {
  isSingleChannelModalOpen.value = true;
  singleChannelModalGroup.value = group;
  singleChannelModalMetricsGroup.value = metricsGroup;
};

const openAllChannelsModal = (group: MetricGroup) => {
  allChannelsModalGroup.value = group;
  allChannelsMetricsGroup.value = allChannelGroups;
  isAllChannelsModalOpen.value = true;
};

const hasMetrics = computed(() =>
  allChannelGroups.every(
    (channelGroup) => channelGroup.metrics && channelGroup.metrics.length > 0,
  ),
);
</script>

<template>
  <PageTitle>
    {{ $t("funnel-flow.home.title") }}

    <template #description>
      {{ $t("funnel-flow.home.description") }}
    </template>
  </PageTitle>

  <!-- Initial View -->
  <template v-if="currentView === 'initial'">
    <div class="tw:grid tw:gap-[18px] tw:lg:grid-cols-3">
      <FunnelFlowHomeCard icon="tabler:plus">
        <template #title>{{
          $t("funnel-flow.home.initial.load-prebuilt.title")
        }}</template>

        <template #description>
          {{ $t("funnel-flow.home.initial.load-prebuilt.description") }}
        </template>

        <template #action>
          <Button
            size="md"
            class="tw:w-full"
            @click="currentView = 'funnelStages'"
            >{{ $t("funnel-flow.home.initial.load-prebuilt.action") }}</Button
          >
        </template>
      </FunnelFlowHomeCard>

      <FunnelFlowHomeCard
        icon="tabler:template"
        class="tw:relative tw:opacity-70"
      >
        <template #title>{{
          $t("funnel-flow.home.initial.create-asset.title")
        }}</template>

        <template #description>
          <div
            class="tw:absolute tw:top-3 tw:right-3 tw:rounded-md tw:bg-secondary/20 tw:px-3 tw:py-1 tw:font-bold"
          >
            {{ $t("global.soon") }}
          </div>
          {{ $t("funnel-flow.home.initial.create-asset.description") }}
        </template>

        <template #action>
          <Button size="md" class="tw:w-full" disabled>
            {{ $t("funnel-flow.home.initial.create-asset.action") }}
          </Button>
        </template>
      </FunnelFlowHomeCard>
    </div>
  </template>

  <!-- Funnel Stages View -->
  <template v-else-if="currentView === 'funnelStages'">
    <div>
      <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-3 tw:md:p-5">
        <div
          class="tw:flex tw:flex-col tw:justify-between tw:gap-6 tw:lg:flex-row"
        >
          <h2 class="tw:text-3xl tw:font-extrabold">
            {{ $t("funnel-flow.home.stages.title") }}
          </h2>

          <!-- <PermissionGuard
            :requires="[{ name: 'FUNNEL_FLOW', actions: ['C'] }]"
          >
            <Button
              leftIcon="tabler-plus"
              variant="text"
              @click="isNewFunnelModalOpen = true"
            >
              {{ $t("funnel-flow.home.stages.new-stage") }}
            </Button>
          </PermissionGuard> -->
        </div>

        <div v-if="hasMetrics" class="tw:flex tw:flex-wrap tw:gap-3">
          <Button
            color="secondary"
            size="sm"
            variant="outlined"
            @click="openAllChannelsModal('Goals')"
          >
            {{ $t("funnel-flow.home.stages.metrics.view-goals") }}
          </Button>

          <Button
            color="secondary"
            size="sm"
            variant="outlined"
            @click="openAllChannelsModal('Resources')"
          >
            {{ $t("funnel-flow.home.stages.metrics.view-resources") }}
          </Button>

          <Button
            color="secondary"
            size="sm"
            variant="outlined"
            @click="openAllChannelsModal('Marketing')"
          >
            {{ $t("funnel-flow.home.stages.metrics.view-marketing") }}
          </Button>
        </div>

        <div class="tw:flex tw:flex-col tw:gap-6">
          <FunnelFlowHomeStageCard
            v-for="stage in allChannelGroups"
            :key="stage.id"
            :data="stage"
            @previewMetrics="
              (metricByGroup) => openSingleChannelModal(metricByGroup, stage)
            "
          />
        </div>
      </CardBase>
    </div>
  </template>

  <FunnelFlowNewFunnelModal v-model="isNewFunnelModalOpen" />

  <FunnelFlowMetricsModalSingleChannel
    v-if="singleChannelModalGroup && singleChannelModalMetricsGroup"
    v-model="isSingleChannelModalOpen"
    :group="singleChannelModalGroup"
    :metricsGroup="singleChannelModalMetricsGroup"
  />

  <FunnelFlowMetricsModalAllChannels
    v-if="allChannelsModalGroup && allChannelGroups"
    v-model="isAllChannelsModalOpen"
    :group="allChannelsModalGroup"
    :metricsGroups="allChannelGroups"
  />
</template>
