<script setup lang="ts">
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import { CampaignNotFoundError } from "@/services/common-errors";

const store = useLucaGuideLayoutStore();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();

const campaignId = String(route.params.campaignId);

usePageTitle(() =>
  t("routes.luca-guide-campaign-onboarding", {
    brand: store.brand?.name ?? "",
  }),
);

const [campaigns, context] = await Promise.all([
  LucaGuideCampaignsApi.list(),
  LucaGuideCampaignsApi.getContext(campaignId),
]);

const campaign = campaigns.find((item) => item.campaign_id === campaignId);

if (!campaign) {
  throw new CampaignNotFoundError();
}

if (campaign.has_primary_kpi) {
  await router.replace({
    name: "LucaGuideCampaign",
    params: {
      brandId: route.params.brandId,
      campaignId,
    },
  });
}
</script>

<template>
  <LucaGuideCampaignOnboarding :campaign="campaign" :context="context" />
</template>
