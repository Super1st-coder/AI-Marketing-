<script setup lang="ts">
import type { ChipProps } from "@/components/chips/Chip.vue";
import type { LucaGuideCampaignHealth } from "@/services/guide/LucaGuideCampaignsApi";

const props = withDefaults(
  defineProps<{
    status: LucaGuideCampaignHealth;
    size?: ChipProps["size"];
  }>(),
  {
    size: "sm",
  },
);

const statusColor = computed(() => {
  switch (props.status) {
    case "pending":
      return "warning";
    case "on_track":
      return "success";
    case "alert":
      return "error";
    case "watch":
      return "warning";
  }
});
</script>

<template>
  <Chip :color="statusColor" variant="label" :size="size" class="tw:uppercase">
    {{ $t(`luca-guide.home.campaigns.statuses.${status}`) }}
  </Chip>
</template>
