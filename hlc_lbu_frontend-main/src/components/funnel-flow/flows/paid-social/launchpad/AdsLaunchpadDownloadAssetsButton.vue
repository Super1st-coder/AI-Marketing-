<script setup lang="ts">
import ChannelConnections from "@/services/funnel-flow/ChannelConnections";

const props = defineProps<{
  creativeId: number;
}>();

const { t } = useI18n();
const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();
const notificationStore = useNotificationStore();

const isDownloading = ref(false);

const handleDownload = async () => {
  if (isDownloading.value) return;

  const creative = preCheckStore.getInitialCreative(props.creativeId);
  if (!creative) return;

  isDownloading.value = true;
  try {
    const zipBlob = await ChannelConnections.exportLaunchAssets({
      brand_id: preCheckStore.brandId,
      campaign_id: preCheckStore.campaignId,
      adset_id: creative.adset_id,
      ad_id: creative.ad_id,
      adchannel_id: creative.adchannel_id,
    });

    downloadBlob(
      zipBlob,
      `${creative.name.replace(/[\\/:*?"<>|]+/g, "-")}.zip`,
    );

    notificationStore.display({
      type: "success",
      title: t(
        "funnel-flow.paid-social.launchpad.common.download-zip-success-title",
      ),
      description: t(
        "funnel-flow.paid-social.launchpad.common.download-zip-success-description",
      ),
    });
  } catch (error) {
    console.error("Failed to download campaign assets:", error);
    notificationStore.display({
      type: "error",
      title: t(
        "funnel-flow.paid-social.launchpad.common.download-zip-error-title",
      ),
      description: t(
        "funnel-flow.paid-social.launchpad.common.download-zip-error-description",
      ),
    });
  } finally {
    isDownloading.value = false;
  }
};
</script>

<template>
  <Button
    type="button"
    variant="label"
    color="primary"
    size="sm"
    leftIcon="tabler:download"
    :shadow="false"
    :isLoading="isDownloading"
    @click="handleDownload"
  >
    {{ $t("funnel-flow.paid-social.launchpad.common.download-zip") }}
  </Button>
</template>
