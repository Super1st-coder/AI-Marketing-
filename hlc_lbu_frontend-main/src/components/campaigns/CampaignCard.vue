<script lang="ts" setup>
import { CampaignData } from "@/services/projects/CampaignsApi";

defineProps<{
  campaign: CampaignData;
}>();
</script>

<template>
  <CardBase class="tw:p-3">
    <!-- Image -->
    <RouterLink
      :to="{
        name: 'CampaignSettings',
        params: { campaignId: campaign.id },
      }"
    >
      <CardDynamicImage
        class="tw:mb-4 tw:aspect-square"
        :src="campaign.thumbnail_url"
      />
    </RouterLink>

    <!-- Title -->
    <RouterLink
      :to="{
        name: 'CampaignSettings',
        params: { campaignId: campaign.id },
      }"
    >
      <h2 class="tw:mb-2.5 tw:text-sm tw:font-bold">
        {{ campaign.name }}
      </h2>
    </RouterLink>

    <!-- Chips -->
    <ChipList class="tw:mb-1.5">
      <ChipCompleted :completed="campaign.complete" />
    </ChipList>
  </CardBase>
</template>
