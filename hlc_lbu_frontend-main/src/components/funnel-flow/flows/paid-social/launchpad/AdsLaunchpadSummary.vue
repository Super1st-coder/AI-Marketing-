<script setup lang="ts">
const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();
</script>

<template>
  <AdsLaunchpadPreCheckContent step="summary" />

  <AdsLaunchpadCampaignUploadSuccessModal
    v-if="preCheckStore.campaignUploadSuccessModalOpen"
    v-model="preCheckStore.campaignUploadSuccessModalOpen"
  />
</template>
