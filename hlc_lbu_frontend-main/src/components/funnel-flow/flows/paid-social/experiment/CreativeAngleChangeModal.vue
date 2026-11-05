<script setup lang="ts">
import AdsApi from "@/services/funnel-flow/paid-social/AdsApi";

const isOpen = defineModel<boolean>({ required: true });

const props = defineProps<{
  adSetId: number;
  channelId: number;
}>();

const brandId = useBrandId();
const campaignId = useCampaignId();

const emit = defineEmits<{
  keepExisting: [];
  deleteAds: [];
}>();

const isKeepingExisting = ref(false);
const isDeletingAds = ref(false);
const isLoading = computed(
  () => isKeepingExisting.value || isDeletingAds.value,
);

async function handleKeepExisting() {
  isKeepingExisting.value = true;
  try {
    emit("keepExisting");
  } finally {
    isKeepingExisting.value = false;
    isOpen.value = false;
  }
}

async function handleDeleteAds() {
  isDeletingAds.value = true;
  try {
    await AdsApi.resetAds({
      brand_id: brandId,
      campaign_id: campaignId,
      ad_set_id: props.adSetId,
      channel_id: props.channelId,
    });

    emit("deleteAds");
  } finally {
    isDeletingAds.value = false;
    isOpen.value = false;
  }
}

function handleCancel() {
  if (isLoading.value) return;
  isOpen.value = false;
}
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    :maxWidth="660"
    @cancel="handleCancel"
    @close="handleCancel"
  >
    <template #title>
      {{ $t("funnel-flow.paid-social.creative-angle.change-modal.title") }}
    </template>

    <template #description>
      {{
        $t("funnel-flow.paid-social.creative-angle.change-modal.description")
      }}
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
            "funnel-flow.paid-social.creative-angle.change-modal.keep-existing-ads",
          )
        }}
      </Button>

      <Button
        type="button"
        :disabled="isLoading"
        :isLoading="isDeletingAds"
        @click="handleDeleteAds"
      >
        {{
          $t("funnel-flow.paid-social.creative-angle.change-modal.delete-ads")
        }}
      </Button>
    </template>
  </ModalGeneric>
</template>
