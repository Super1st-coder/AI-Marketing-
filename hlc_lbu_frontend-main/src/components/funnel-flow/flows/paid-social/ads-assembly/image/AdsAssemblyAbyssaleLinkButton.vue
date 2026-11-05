<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import AdStructureApi from "@/services/funnel-flow/paid-social/AdStructureApi";

const store = useFunnelPaidSocialAdsAssemblyStore();
const paidSocialFormStore = useFunnelPaidSocialFormStore();

const isOpen = ref(false);

function handleClick() {
  isOpen.value = true;
}

async function handleDisconnect() {
  if (!store.currentSet) {
    throw new UnidentifiedError();
  }

  // Set the project to null
  await AdStructureApi.SetAbbysaleProjectToAdSet({
    brand_id: store.brandId,
    campaign_id: store.campaign.id,
    ad_set_id: store.currentSet?.id,
    media_platform_project_id: null,
  });

  // Refetch ad sets and revalidate funnel flow so the linked project id is
  // updated
  await Promise.all([store.refetchAdSets(), paidSocialFormStore.revalidate()]);

  // Take the user to the first screen
  store.setScreen("assetOrigin");
}
</script>

<template>
  <Button
    size="xs"
    :uppercase="false"
    class="tw:max-w-full tw:overflow-hidden tw:text-ellipsis tw:whitespace-nowrap tw:md:max-w-[124px]"
    type="button"
    color="success"
    variant="label"
    @click="handleClick"
  >
    {{
      $t("funnel-flow.paid-social.ads.origin.connected-chip", {
        projectId: store.currentAssetOrigin?.project_id,
      })
    }}

    <ModalGeneric
      v-model="isOpen"
      :maxWidth="600"
      :confirmFn="handleDisconnect"
    >
      <template #title>
        {{ $t("funnel-flow.paid-social.ads.origin.connected-modal.title") }}
      </template>

      <template #description>
        {{
          $t("funnel-flow.paid-social.ads.origin.connected-modal.description")
        }}
      </template>

      <CardBase class="tw:p-6">
        <div class="tw:mb-6 tw:flex tw:justify-between">
          <div class="tw:font-medium">
            {{
              $t(
                "funnel-flow.paid-social.ads.origin.connected-modal.project-name",
              )
            }}
          </div>

          <div class="tw:text-secondary-text">
            {{ store.currentAssetOrigin?.project_name }}
          </div>
        </div>

        <div class="tw:flex tw:justify-between">
          <div class="tw:font-medium">
            {{
              $t(
                "funnel-flow.paid-social.ads.origin.connected-modal.project-id",
              )
            }}
          </div>

          <div class="tw:text-secondary-text">
            {{ store.currentAssetOrigin?.project_id }}
          </div>
        </div>
      </CardBase>

      <template #continue>
        {{
          $t(
            "funnel-flow.paid-social.ads.origin.connected-modal.disconnect-project",
          )
        }}
      </template>

      <template #cancel>
        {{ $t("global.cancel") }}
      </template>
    </ModalGeneric>
  </Button>
</template>
