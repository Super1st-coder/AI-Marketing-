<script setup lang="ts">
import { FunnelPaidSocialFormData } from "../FunnelPaidSocialForm.vue";

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();

const { data } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const store = useFunnelPaidSocialAdsAssemblyStore();

await store.initialize(
  brandId,
  projectId,
  campaignId,
  data.value.channelGroupId,
);

const isFormatModalOpen = computed<boolean>({
  get: () => store.formatModalAdSetId !== undefined,
  set: (value) => {
    if (!value) {
      store.closeFormatModal();
    }
  },
});
</script>

<template>
  <FunnelPaidSocialFormNewSideBar
    :items="store.menu"
    :key="store.currentSet?.id"
  >
    <Suspense suspensible :timeout="0">
      <!-- Image flow -->
      <AdsAssemblyHome v-if="store.currentScreen === 'home'" />
      <AdsAssemblyAssetOrigin
        v-else-if="store.currentScreen === 'assetOrigin'"
      />
      <AdsAssemblySettings v-else-if="store.currentScreen === 'settings'" />
      <AdsAssemblyRefine
        v-else-if="store.currentScreen === 'refine'"
        :key="store.currentAd?.ad_id"
      />

      <!-- Video flow -->
      <!-- Keyed by the ad, so each screen is built from its variants and not
        reused with the state of the previous ad. The keys differ because a
        v-if chain needs unique ones -->
      <AdsAssemblyVideoSettings
        v-else-if="store.currentScreen === 'videoSettings'"
        :key="`videoSettings-${store.currentAd?.ad_id}`"
      />
      <AdsAssemblyVideoScripts
        v-else-if="store.currentScreen === 'videoScripts'"
        :key="`videoScripts-${store.currentAd?.ad_id}`"
      />
      <AdsAssemblyVideoStoryboard
        v-else-if="store.currentScreen === 'videoStoryboard'"
        :key="`videoStoryboard-${store.currentAd?.ad_id}`"
      />
      <AdsAssemblyVideoVoiceover
        v-else-if="store.currentScreen === 'videoVoiceover'"
        :key="`videoVoiceover-${store.currentAd?.ad_id}`"
      />
      <!-- The last step reuses the image flow's Select & Refine screen -->
      <AdsAssemblyRefine
        v-else-if="store.currentScreen === 'videoAd'"
        :key="`videoAd-${store.currentAd?.ad_id}`"
      />

      <template #fallback>
        <CircleLoaderDefault class="tw:min-h-[calc(100vh-66px)] tw:w-full" />
      </template>
    </Suspense>
  </FunnelPaidSocialFormNewSideBar>

  <AdsAssemblyAdFormatModal
    v-if="store.formatModalAdSetId !== undefined"
    v-model="isFormatModalOpen"
    :adGroupId="store.formatModalAdSetId"
  />
</template>
