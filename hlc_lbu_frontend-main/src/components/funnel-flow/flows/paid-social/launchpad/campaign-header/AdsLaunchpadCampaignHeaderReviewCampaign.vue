<script setup lang="ts">
import { CampaignData } from "@/services/projects/CampaignsApi";

defineProps<{
  campaign: CampaignData;
}>();
</script>

<template>
  <TextWithOverflow class="tw:text-sm tw:text-secondary" variant="chevron">
    {{ campaign.description }} <br />

    {{
      $t("funnel-flow.paid-social.launchpad.common.review-campaign-description")
    }}

    <template #buttonContent="{ isExpanded }">
      <span>
        {{
          isExpanded
            ? $t("funnel-flow.paid-social.launchpad.common.view-less")
            : $t("funnel-flow.paid-social.launchpad.common.view-full-analysis")
        }}
      </span>
    </template>
  </TextWithOverflow>
</template>
