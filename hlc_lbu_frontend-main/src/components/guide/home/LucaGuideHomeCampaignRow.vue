<script setup lang="ts">
import type { LucaGuideCampaignHealth } from "@/services/guide/LucaGuideCampaignsApi";

defineProps<{
  id: string;
  name: string;
  adsCount: number;
  status?: LucaGuideCampaignHealth;
  hasContext: boolean;
  objective?: string;
}>();
</script>

<template>
  <div
    class="tw:flex tw:flex-col tw:gap-5 tw:py-4 tw:pr-3 tw:pl-6 tw:lg:flex-row tw:lg:items-center tw:lg:justify-between"
  >
    <div v-if="status" class="tw:shrink-0">
      <LucaGuideCampaignStatusChip :status="status" />
    </div>

    <LucaGuideCampaignIdentity
      :name="name"
      :objective="objective"
      :hasContext="hasContext"
    />

    <Link
      :to="{ name: 'LucaGuideCampaign', params: { campaignId: id } }"
      icon="tabler:chevron-right"
      class="tw:shrink-0 tw:text-sm tw:font-medium"
    >
      {{ $t("luca-guide.home.campaigns.view-campaign") }}
    </Link>
  </div>
</template>
