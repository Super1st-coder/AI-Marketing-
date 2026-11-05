<script lang="ts" setup>
import { UmbrellaCampaignData } from "@/services/projects/UmbrellaCampaignsApi";
import { RouteLocationRaw, RouterLink } from "vue-router";

const props = defineProps<{
  data: UmbrellaCampaignData;
  interactable?: boolean;
}>();

const route = computed<RouteLocationRaw | undefined>(() =>
  props.interactable
    ? {
        name: "UmbrellaCampaignSettings",
        params: { umbrellaCampaignId: props.data.id },
      }
    : undefined,
);
</script>

<template>
  <CardBase class="tw:p-3">
    <component :is="interactable ? RouterLink : 'div'" :to="route">
      <CardDynamicImage
        class="tw:mb-4 tw:aspect-square"
        :src="data.thumbnail_url"
      />
    </component>

    <component :is="interactable ? RouterLink : 'div'" :to="route">
      <h2 class="tw:mb-2.5 tw:text-sm tw:font-bold">
        {{ data.name }}
      </h2>
    </component>

    <!-- Chips -->
    <ChipList>
      <ChipCompleted :completed="data.complete" />
    </ChipList>
  </CardBase>
</template>
