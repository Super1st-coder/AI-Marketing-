<script lang="ts" setup>
import CampaignsApi from "@/services/projects/CampaignsApi";

const { t } = useI18n();
const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();
const campaign = (await CampaignsApi.getOne(brandId, projectId, campaignId))
  .data;

usePageTitle(() => t("routes.funnel-paid-social", { campaign: campaign.name }));
</script>

<template>
  <FunnelPaidSocialForm />
</template>
