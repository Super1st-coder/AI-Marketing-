<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import {
  AudienceItem,
  AudiencesByChannel,
} from "@/services/projects/AudienceApi";

const brandId = useBrandId();
const campaignId = useCampaignId();

const wizard = useFunnelPaidSocialAudienceStore();

const audienceIdRef = ref<number>();
const channelIdRef = ref<number>();
const audienceSelectedRef = ref<AudienceItem>();

const props = defineProps<{
  title: string;
  description: string;
  audiences: AudiencesByChannel[];
  currentTab: number | null;
  audiencesType: "generated" | "saved";
}>();

const emit = defineEmits<(e: "useAudience") => void>();

// Modal state for audience change confirmation
const showAudienceChangeModal = ref(false);

function audienceSelected(audience: AudienceItem, channelId: number) {
  audienceIdRef.value = audience.id;
  channelIdRef.value = channelId;
  audienceSelectedRef.value = audience;
}

async function handleUseAudience() {
  // Check if ad set has filled ads using the store
  if (wizard.selectedAdSetHasFilledAds) {
    showAudienceChangeModal.value = true;
  } else {
    await setPreferredAudience();
  }
}

async function setPreferredAudience() {
  if (
    channelIdRef.value == null ||
    audienceIdRef.value == null ||
    audienceSelectedRef.value == null
  ) {
    throw new UnidentifiedError();
  }

  if (props.audiencesType === "generated") {
    await wizard.setPreferredAudience({
      brand_id: brandId,
      campaign_id: campaignId,
      ad_set_id: wizard.selectedAdSet.id,
      channel_id: channelIdRef.value,
      preferred_audience_id: audienceIdRef.value,
    });
  } else if (props.audiencesType === "saved") {
    await wizard.createAudienceFromSaved({
      brand_id: brandId,
      campaign_id: campaignId,
      ad_set_id: wizard.selectedAdSet.id,
      channel_id: channelIdRef.value,
      audience: audienceSelectedRef.value,
    });
  }

  wizard.setStep("END_MESSAGE");
}

async function cancelProposalAudiences() {
  emit("useAudience");
}
</script>

<template>
  <h2 class="tw:mb-4 tw:text-2xl tw:font-extrabold">
    {{ props.title }}
  </h2>

  <p class="tw:mb-5">
    {{ props.description }}
  </p>

  <template v-if="props.currentTab !== null">
    <Tabs v-model="props.currentTab">
      <template #list>
        <Tab
          v-for="channel in props.audiences"
          :value="channel.channel_id"
          :key="channel.channel_id"
          >{{ channel.channel_name }}</Tab
        >
      </template>
      <TabsPanels>
        <TabPanel
          v-for="channel in props.audiences"
          :value="channel.channel_id"
          :key="channel.channel_id"
        >
          <div
            class="tw:grid tw:gap-3"
            :class="
              !channel[
                audiencesType === 'generated'
                  ? 'proposal_audiences'
                  : 'saved_audiences'
              ]?.length
                ? 'tw:grid-cols-1'
                : 'tw:grid-cols-1 tw:md:grid-cols-2 tw:lg:grid-cols-3'
            "
          >
            <template
              v-for="audience in channel[
                audiencesType === 'generated'
                  ? 'proposal_audiences'
                  : 'saved_audiences'
              ]"
              :key="audience.id"
            >
              <FunnelPaidSocialFormAudienceItem
                :channelId="channel.channel_id"
                :audience-type="channel.saved_audiences ? 'saved' : 'generated'"
                :audience="audience"
                @audience-selected="
                  audienceSelected(audience, channel.channel_id)
                "
              />
            </template>

            <template
              v-if="
                !channel[
                  audiencesType === 'generated'
                    ? 'proposal_audiences'
                    : 'saved_audiences'
                ]?.length
              "
            >
              <div
                class="tw:flex tw:w-full tw:items-center tw:justify-center tw:py-10"
              >
                <p
                  class="tw:text-center tw:text-lg tw:font-medium tw:text-gray-500"
                >
                  {{
                    audiencesType === "generated"
                      ? $t(
                          "funnel-flow.paid-social.audience.saved-audience.empty-states.channel-generated",
                        )
                      : $t(
                          "funnel-flow.paid-social.audience.saved-audience.empty-states.channel-saved",
                        )
                  }}
                </p>
              </div>
            </template>
          </div>
        </TabPanel>
      </TabsPanels>
    </Tabs>
  </template>

  <template v-if="!props.audiences.length">
    <hr class="tw:-mx-10 tw:my-5 tw:border-secondary/30" />
    <div class="tw:flex tw:w-full tw:items-center tw:justify-center tw:py-10">
      <p class="tw:text-center tw:text-lg tw:font-medium tw:text-gray-500">
        {{
          audiencesType === "generated"
            ? $t(
                "funnel-flow.paid-social.audience.saved-audience.empty-states.global-generated",
              )
            : $t(
                "funnel-flow.paid-social.audience.saved-audience.empty-states.global-saved",
              )
        }}
      </p>
    </div>
  </template>

  <div>
    <hr class="tw:-mx-10 tw:my-5 tw:border-secondary/30" />
    <div class="tw:flex tw:justify-end tw:gap-5">
      <Button
        size="md"
        type="button"
        variant="outlined"
        @click="cancelProposalAudiences"
      >
        {{ $t("global.cancel") }}
      </Button>
      <Button
        :disabled="!props.audiences.length || !audienceSelectedRef"
        size="md"
        type="button"
        @click="handleUseAudience"
      >
        {{ $t("audience.ai-research.saved-audience.use-audience-btn") }}
      </Button>
    </div>
  </div>

  <!-- Target Audience Changed Modal -->
  <FunnelPaidSocialFormAudienceChangeModal
    v-if="channelIdRef != null"
    v-model="showAudienceChangeModal"
    :adSetId="wizard.selectedAdSet.id"
    :channelId="channelIdRef"
    @confirm="setPreferredAudience"
  />
</template>

<style></style>
