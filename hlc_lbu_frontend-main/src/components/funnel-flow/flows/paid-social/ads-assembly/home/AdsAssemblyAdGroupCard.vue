<script setup lang="ts">
const props = defineProps<{ data: AdStructureWithAudienceAndCreativeAngle }>();

const store = useFunnelPaidSocialAdsAssemblyStore();

const completedCount = computed(() => {
  // Get the ads for this ad set
  const ads = props.data.ads.map((ad) => store.ads[ad.id]);

  // Count the ads that has been completed
  const count = ads.reduce((previousValue, currentValue) => {
    return previousValue + (store.isAdCompleted(currentValue) === true ? 1 : 0);
  }, 0);

  return count;
});
</script>

<template>
  <CardBase class="tw:grid tw:grid-cols-1 tw:gap-2 tw:p-6">
    <div class="tw:flex tw:flex-col tw:justify-between tw:gap-2 tw:xl:flex-row">
      <h2 class="tw:text-xl tw:font-bold">
        {{ data.name }}
      </h2>

      <div>
        <Link
          is="button"
          icon="tabler:chevron-right"
          class="tw:text-sm tw:whitespace-nowrap"
          @click="store.openAdSet(data.id)"
        >
          {{
            $t("funnel-flow.paid-social.ads.ad-groups.selected-count", {
              selected: completedCount,
              total: data.ads.length,
            })
          }}
        </Link>
      </div>
    </div>

    <p
      v-if="store.currentSet?.description"
      class="tw:text-sm tw:text-secondary-text"
    >
      {{ store.currentSet.description }}
    </p>

    <div class="tw:flex tw:flex-wrap tw:gap-4">
      <AudienceButton
        :audience="
          data.audiences.find((channel) => channel.preferred_audience != null)
            ?.preferred_audience ?? undefined
        "
      />

      <CreativeAngleButton :creativeAngle="data.experiment" />
    </div>
  </CardBase>
</template>
