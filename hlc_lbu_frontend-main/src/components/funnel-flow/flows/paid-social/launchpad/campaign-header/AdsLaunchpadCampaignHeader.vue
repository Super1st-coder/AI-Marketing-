<script setup lang="ts">
import {
  CampaignChannelGroupData,
  CampaignData,
} from "@/services/projects/CampaignsApi";
import { FunnelPaidSocialFormData } from "../../FunnelPaidSocialForm.vue";
import { MetricGroup } from "@/services/UtilsApi";

defineProps<{
  campaign: CampaignData;
}>();

const { data } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const strategyDetailsModal = ref(false);
const isSingleChannelModalOpen = ref<boolean>(false);
const singleChannelModalGroup = ref<MetricGroup | undefined>();
const singleChannelModalMetricsGroup = ref<
  CampaignChannelGroupData | undefined
>();

const metricsByFunnelStages = (metricByGroup: MetricGroup) => {
  singleChannelModalGroup.value = metricByGroup;
  singleChannelModalMetricsGroup.value = data.value.channelGroup;
  isSingleChannelModalOpen.value = true;
};
</script>

<template>
  <CardBase class="tw:grid tw:grid-cols-1 tw:gap-5 tw:p-6">
    <div class="tw:flex tw:items-start tw:gap-3">
      <IconCard icon="tabler-speakerphone" variant="success" size="lg" />

      <div class="tw:grid tw:grid-cols-1 tw:gap-2">
        <div
          class="tw:flex tw:flex-col tw:gap-2 tw:md:flex-row tw:md:items-center tw:md:justify-between tw:md:gap-5"
        >
          <h2 class="tw:text-xl tw:font-bold">
            {{ campaign.name }}
          </h2>

          <div
            v-if="$slots.actions"
            class="tw:flex tw:shrink-0 tw:items-center tw:gap-4"
          >
            <slot name="actions" />
          </div>
        </div>

        <slot />
      </div>
    </div>

    <!-- Separator -->
    <Separator />

    <!-- Tab Buttons -->
    <div class="tw:flex tw:flex-col tw:gap-4 tw:lg:flex-row">
      <Button
        variant="outlined"
        color="secondary"
        size="sm"
        @click="strategyDetailsModal = true"
        type="button"
        :shadow="false"
      >
        {{ $t("funnel-flow.paid-social.launchpad.common.strategy-details") }}
      </Button>
      <Button
        variant="outlined"
        color="secondary"
        size="sm"
        @click="metricsByFunnelStages('Goals')"
        type="button"
        :shadow="false"
      >
        {{ $t("funnel-flow.paid-social.launchpad.common.paid-social-goals") }}
      </Button>
      <Button
        variant="outlined"
        color="secondary"
        size="sm"
        @click="metricsByFunnelStages('Resources')"
        type="button"
        :shadow="false"
      >
        {{
          $t("funnel-flow.paid-social.launchpad.common.paid-social-resources")
        }}
      </Button>
      <Button
        variant="outlined"
        color="secondary"
        size="sm"
        @click="metricsByFunnelStages('Marketing')"
        type="button"
        :shadow="false"
      >
        {{ $t("funnel-flow.paid-social.launchpad.common.paid-social-kpis") }}
      </Button>
    </div>

    <!-- Strategy Details Modal -->
    <Modal
      :modelValue="strategyDetailsModal"
      @update:modelValue="
        () => {
          strategyDetailsModal = false;
        }
      "
      class="tw:p-10"
      :maxWidth="640"
      closeButton
    >
      <h2 class="tw:mb-2 tw:text-2xl tw:font-bold">
        {{
          $t(
            "funnel-flow.paid-social.launchpad.common.campaign-strategic-details",
          )
        }}
      </h2>
      <p class="tw:mb-6 tw:text-secondary">
        {{
          $t(
            "funnel-flow.paid-social.launchpad.common.campaign-strategic-details-description",
          )
        }}
      </p>

      <CardBase class="tw:p-5">
        <div class="tw:flex tw:items-center tw:justify-between tw:py-3">
          <span class="tw:font-semibold">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.common.funnel-stage-strategy",
              )
            }}
          </span>
          <span class="tw:text-secondary">{{ campaign.funnel?.name }}</span>
        </div>

        <div
          class="tw:flex tw:items-center tw:justify-between tw:border-b tw:border-gray-200 tw:py-3"
        >
          <span class="tw:font-semibold">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.common.geographic-targeting",
              )
            }}
          </span>
          <span class="tw:text-secondary">{{ campaign.target_regions }}</span>
        </div>

        <div class="tw:py-4">
          <h4 class="tw:mb-2 tw:font-semibold">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.common.creative-concept-narrative",
              )
            }}
          </h4>
          <p class="tw:text-secondary">{{ campaign.description }}</p>
        </div>

        <div class="tw:border-t tw:border-gray-200 tw:pt-4">
          <h4 class="tw:mb-6 tw:font-semibold">
            {{
              $t("funnel-flow.paid-social.launchpad.common.user-journey-path")
            }}
          </h4>
          <div class="tw:space-y-5">
            <div class="tw:flex tw:gap-3">
              <div
                class="tw:mt-1.5 tw:h-2 tw:w-2 tw:shrink-0 tw:rounded-full tw:bg-primary/60"
              />
              <div>
                <p class="tw:font-medium">
                  {{
                    campaign.preferred_campaign?.sections?.funnel_flow?.title
                  }}
                </p>
                <p
                  class="tw:mt-2 tw:leading-relaxed tw:whitespace-pre-line tw:text-secondary"
                >
                  {{ campaign.preferred_campaign?.sections?.funnel_flow?.text }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </CardBase>
    </Modal>

    <FunnelFlowMetricsModalSingleChannel
      v-if="singleChannelModalGroup && singleChannelModalMetricsGroup"
      v-model="isSingleChannelModalOpen"
      :group="singleChannelModalGroup"
      :metricsGroup="singleChannelModalMetricsGroup"
    />
  </CardBase>
</template>
