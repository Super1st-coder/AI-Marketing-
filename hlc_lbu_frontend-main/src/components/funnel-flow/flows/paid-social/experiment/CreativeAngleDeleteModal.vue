<script setup lang="ts">
import AdsApi from "@/services/funnel-flow/paid-social/AdsApi";

const isOpen = defineModel<boolean>({ required: true });

const store = useFunnelPaidSocialExperimentStore();
const formStore = useFunnelPaidSocialFormStore();
const brandId = useBrandId();
const campaignId = useCampaignId();

const isKeepingExisting = ref(false);
const isDeletingAds = ref(false);
const isLoading = computed(
  () => isKeepingExisting.value || isDeletingAds.value,
);

watch(isOpen, (open) => {
  if (!open) {
    isKeepingExisting.value = false;
    isDeletingAds.value = false;
  }
});

async function handleKeepExisting() {
  isKeepingExisting.value = true;
  await store.deleteCurrentExperiment();
  isOpen.value = false;
  isKeepingExisting.value = false;
}

async function handleDeleteAds() {
  isDeletingAds.value = true;
  await AdsApi.resetAds({
    brand_id: brandId,
    campaign_id: campaignId,
    ad_set_id: store.selectedAdSet.id,
    channel_id: store.channelGroupId,
  });
  await store.deleteCurrentExperiment();
  isOpen.value = false;
}

function handleCancel() {
  if (isLoading.value) return;
  isOpen.value = false;
}
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    :maxWidth="560"
    @cancel="handleCancel"
    @close="handleCancel"
  >
    <template #title>
      {{ $t("funnel-flow.paid-social.creative-angle.main.delete-modal.title") }}
    </template>

    <p class="tw:mb-2 tw:text-secondary-text">
      {{
        $t(
          "funnel-flow.paid-social.creative-angle.main.delete-modal.dependency-description",
          {
            subcategory: store.currentExperiment?.subcategory?.name,
            adSetName: store.selectedAdSet?.name,
            adCount: formStore.countFilledAds(store.selectedAdSet?.id ?? 0),
          },
        )
      }}
    </p>

    <p class="tw:text-sm tw:text-secondary tw:italic">
      {{
        $t(
          "funnel-flow.paid-social.creative-angle.main.delete-modal.dependency-impact",
        )
      }}
    </p>

    <template #footerBefore>
      <Button
        variant="outlined"
        type="button"
        :disabled="isLoading"
        @click="handleCancel"
      >
        {{ $t("global.cancel") }}
      </Button>
    </template>

    <template #actions>
      <Button
        variant="outlined"
        type="button"
        :disabled="isLoading"
        :isLoading="isKeepingExisting"
        @click="handleKeepExisting"
      >
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.main.delete-modal.keep-existing-ads",
          )
        }}
      </Button>

      <Button
        color="error"
        type="button"
        :disabled="isLoading"
        :isLoading="isDeletingAds"
        @click="handleDeleteAds"
      >
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.main.delete-modal.reset-ads",
          )
        }}
      </Button>
    </template>
  </ModalGeneric>
</template>
