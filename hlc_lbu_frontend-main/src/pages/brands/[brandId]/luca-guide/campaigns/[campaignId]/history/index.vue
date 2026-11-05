<script setup lang="ts">
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import { CampaignNotFoundError } from "@/services/common-errors";

const store = useLucaGuideLayoutStore();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const campaignId = String(route.params.campaignId);

const campaigns = await LucaGuideCampaignsApi.list();
const campaign = campaigns.find((item) => item.campaign_id === campaignId);

if (!campaign) {
  throw new CampaignNotFoundError();
}

if (!campaign.has_primary_kpi) {
  await router.replace({
    name: "LucaGuideCampaignOnboarding",
    params: {
      brandId: route.params.brandId,
      campaignId,
    },
  });
}

usePageTitle(() =>
  t("routes.luca-guide-campaign-history", {
    brand: store.brand?.name ?? "",
    campaign: campaign.name,
  }),
);

const breadcrumbs = computed(() => [
  {
    label: t("luca-guide.campaigns.label"),
    to: { name: "LucaGuideCampaigns" },
  },
  {
    label: t("luca-guide.campaigns.detail.performance-label"),
    to: {
      name: "LucaGuideCampaign",
      params: { campaignId },
    },
  },
  {
    label: t("luca-guide.campaigns.history.title"),
  },
]);
</script>

<template>
  <div class="tw:flex tw:h-full tw:flex-col">
    <div class="tw:border-b tw:border-divider tw:px-7 tw:py-2">
      <Breadcrumbs :data="breadcrumbs" />
    </div>

    <ContainerDashboard>
      <PageTitle>
        {{ $t("luca-guide.campaigns.history.title") }}

        <template #description>
          <i18n-t keypath="luca-guide.campaigns.history.description">
            <template #campaign>
              <span class="tw:font-bold">{{ campaign.name }}</span>
            </template>
          </i18n-t>
        </template>
      </PageTitle>

      <!-- TODO: add a table and wire up the backend -->
      <p class="tw:text-secondary-text">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim
        veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea
        commodo consequat. Duis aute irure dolor in reprehenderit in voluptate
        velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint
        occaecat cupidatat non proident, sunt in culpa qui officia deserunt
        mollit anim id est laborum.
      </p>
    </ContainerDashboard>
  </div>
</template>
