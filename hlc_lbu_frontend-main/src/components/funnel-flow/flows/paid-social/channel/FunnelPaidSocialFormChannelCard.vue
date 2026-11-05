<script setup lang="ts">
import { computed, ref } from "vue";
import { FunnelFlowChannel } from "@/services/funnel-flow/FunnelFlowApi";
import { useFunnelPaidSocialFormStore } from "@/stores/funnel-flow/paid-social/FunnelPaidSocialFormStore";

const props = defineProps<{
  channelGroup: FunnelFlowChannel;
  isSaving: boolean;
  activeChannelCount: number;
  primaryChannel?: FunnelFlowChannel;
}>();

const _isSelected = defineModel<boolean>({ required: true, default: false });
const showDeleteChannelModal = ref(false);
const showConfirmRootChannelModal = ref(false);

const paidSocialFormStore = useFunnelPaidSocialFormStore();

// Calculate asset counts for this channel from funnel_flow_data
const channelAssetCounts = computed(() => {
  const validatorData = paidSocialFormStore.currentValidation?.funnel_flow_data;
  if (!validatorData || !props.channelGroup.id) {
    return { audiences: 0, ads: 0 };
  }

  let adsCount = 0;
  let audiencesCount = 0;

  // Count ads and audiences for this channel across all ad sets
  validatorData.forEach((adSet) => {
    // Count ads for this channel
    adSet.ads.forEach((ad) => {
      const hasChannel = ad.attributes.ad_channels.some(
        (channel) => channel.channel_id === props.channelGroup.id,
      );
      if (hasChannel) {
        adsCount++;
      }
    });

    // Count audiences for this channel
    const hasAudienceForChannel = adSet.audiences.some(
      (audience) => audience.channel_id === props.channelGroup.id,
    );
    if (hasAudienceForChannel) {
      audiencesCount++;
    }
  });

  return {
    audiences: audiencesCount,
    ads: adsCount,
  };
});

const isDisabled = computed(
  () =>
    !props.channelGroup.active ||
    props.isSaving ||
    props.primaryChannel?.id === props.channelGroup.id,
);

const isCheckboxSelected = computed({
  get: () => {
    return _isSelected.value;
  },
  set: (value) => {
    // Display delete channel modal if the channel is selected
    if (_isSelected.value) {
      showDeleteChannelModal.value = true;
      return;
    }

    // Display confirm root channel modal if the channel is not selected and there are no active channels
    if (!_isSelected.value && props.activeChannelCount === 0) {
      showConfirmRootChannelModal.value = true;
      return;
    }

    _isSelected.value = value;
  },
});

const handleConfirmRootChannel = async () => {
  _isSelected.value = true;
};

const handleCancelRootChannel = () => {
  _isSelected.value = false;
};

const handleConfirmDeleteChannel = async () => {
  _isSelected.value = false;
};

const handleCancelDeleteChannel = () => {
  _isSelected.value = true;
};
</script>

<template>
  <CardBase
    is="label"
    class="tw:relative tw:cursor-pointer tw:rounded-lg! tw:p-6"
    :outlineColor="channelGroup.active ? 'primary' : 'default'"
    :disabled="isDisabled"
  >
    <CustomCheckbox
      v-model="isCheckboxSelected"
      :label="channelGroup.name"
      :disabled="isDisabled"
    />

    <Chip
      v-if="!channelGroup.active"
      size="md"
      class="tw:absolute tw:top-1 tw:right-1"
    >
      {{ $t("global.soon") }}
    </Chip>

    <!-- Delete channel modal -->
    <ModalGeneric
      v-model="showDeleteChannelModal"
      :maxWidth="660"
      @confirm="handleConfirmDeleteChannel"
      @cancel="handleCancelDeleteChannel"
    >
      <template #title>
        {{
          $t("funnel-flow.paid-social.channel.modals.delete-channel.title", {
            channel: channelGroup.name || "",
          })
        }}
      </template>

      <template #description>
        <i18n-t
          keypath="funnel-flow.paid-social.channel.modals.delete-channel.description"
          tag="div"
        >
          <template #channel>
            {{ channelGroup.name }}
          </template>

          <template #list>
            <ul class="tw:list-disc tw:pl-6">
              <li>
                {{
                  $t(
                    "funnel-flow.paid-social.channel.modals.delete-channel.audiences",
                    {
                      count: channelAssetCounts?.audiences ?? 0,
                    },
                  )
                }}
              </li>
              <li>
                {{
                  $t(
                    "funnel-flow.paid-social.channel.modals.delete-channel.ads",
                    {
                      count: channelAssetCounts?.ads ?? 0,
                    },
                  )
                }}
              </li>
            </ul>
          </template>

          <template #activeChannel>
            {{ props.primaryChannel?.name }}
          </template>
        </i18n-t>
      </template>

      <template #continue>
        {{
          $t("funnel-flow.paid-social.channel.modals.delete-channel.confirm")
        }}
      </template>

      <template #cancel>
        {{ $t("global.cancel") }}
      </template>
    </ModalGeneric>

    <!-- Confirm Primary Channel Modal -->
    <ModalGeneric
      v-model="showConfirmRootChannelModal"
      :maxWidth="660"
      @confirm="handleConfirmRootChannel"
      @cancel="handleCancelRootChannel"
    >
      <template #title>
        {{
          $t(
            "funnel-flow.paid-social.channel.modals.confirm-root-channel.title",
          )
        }}
      </template>

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.channel.modals.confirm-root-channel.description",
            {
              channel: channelGroup.name,
            },
          )
        }}
      </template>

      <template #continue>
        {{
          $t(
            "funnel-flow.paid-social.channel.modals.confirm-root-channel.confirm",
          )
        }}
      </template>

      <template #cancel>
        {{ $t("global.cancel") }}
      </template>
    </ModalGeneric>
  </CardBase>
</template>
