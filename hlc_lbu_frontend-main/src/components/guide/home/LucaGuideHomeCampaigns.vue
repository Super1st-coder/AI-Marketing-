<script setup lang="ts">
import { type LucaGuideCampaign } from "@/services/guide/LucaGuideCampaignsApi";

const props = defineProps<{
  campaigns: LucaGuideCampaign[];
}>();

const activeCampaigns = props.campaigns.filter(
  (campaign) => campaign.has_primary_kpi,
);
const pendingCampaigns = props.campaigns.filter(
  (campaign) => !campaign.has_primary_kpi,
);

const currentTab = ref("active");
</script>

<template>
  <CardBase class="tw:flex tw:h-full tw:flex-col tw:overflow-hidden">
    <h2
      class="tw:flex tw:items-center tw:gap-2 tw:p-4 tw:pb-2 tw:text-xl tw:font-bold"
    >
      <Icon icon="tabler:speakerphone" class="tw:text-[24px]" />

      <span>{{ $t("luca-guide.home.campaigns.title") }}</span>
    </h2>

    <Tabs v-model="currentTab" size="sm">
      <template #list>
        <Tab value="active" icon="tabler:chart-dots">
          {{ $t("luca-guide.home.campaigns.tabs.active") }}
        </Tab>

        <Tab value="pending" icon="tabler:hourglass">
          {{ $t("luca-guide.home.campaigns.tabs.pending") }}
        </Tab>
      </template>

      <TabPanel
        value="active"
        class="tw:overflow-y-scroll"
        style="height: 303px"
      >
        <div
          v-if="activeCampaigns.length"
          class="tw:flex tw:flex-col tw:divide-y tw:divide-gray-300"
        >
          <LucaGuideHomeCampaignRow
            v-for="campaign in activeCampaigns"
            :key="campaign.campaign_id"
            :id="campaign.campaign_id"
            :name="campaign.name"
            :adsCount="campaign.ad_count"
            :status="campaign.health"
            :hasContext="campaign.context_status === 'with'"
            :objective="campaign.objective"
          />
        </div>

        <LucaGuideEmptyState
          v-else
          :title="$t('luca-guide.home.campaigns.empty.active.title')"
          :description="
            $t('luca-guide.home.campaigns.empty.active.description')
          "
        >
          <Button type="button" size="md" @click="currentTab = 'pending'">
            {{
              $t("luca-guide.home.campaigns.empty.active.button", {
                count: pendingCampaigns.length,
              })
            }}
          </Button>
        </LucaGuideEmptyState>
      </TabPanel>

      <TabPanel
        value="pending"
        class="tw:overflow-y-scroll"
        style="height: 303px"
      >
        <div
          v-if="pendingCampaigns.length"
          class="tw:flex tw:flex-col tw:divide-y tw:divide-gray-300"
        >
          <LucaGuideHomeCampaignRow
            v-for="campaign in pendingCampaigns"
            :key="campaign.campaign_id"
            :id="campaign.campaign_id"
            :name="campaign.name"
            :adsCount="campaign.ad_count"
            :hasContext="campaign.context_status === 'with'"
            :objective="campaign.objective"
          />
        </div>

        <LucaGuideEmptyState
          v-else
          :title="$t('luca-guide.home.campaigns.empty.pending.title')"
          :description="
            $t('luca-guide.home.campaigns.empty.pending.description')
          "
        />
      </TabPanel>
    </Tabs>
  </CardBase>
</template>
