<script setup lang="ts">
import { AdVariant } from "@/services/funnel-flow/paid-social/AdsApi";

const { t, locale } = useI18n();

const isOpen = defineModel<boolean>({ required: true });

const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

function remainingAssetCount(total: number): number {
  return Math.max(total - 1, 0);
}

function countPayloads(variant: AdVariant, name: string): number {
  return (
    variant.channel_attributes?.find((attribute) => attribute.name === name)
      ?.payloads.length ?? 0
  );
}

function remainingAssetsSummary(creativeId: number) {
  const variant = preCheckStore.getInitialCreative(creativeId)?.adVariant;
  assert(variant, "AdVariant should exist for the given creativeId");

  const totalImages = variant.media.formats?.length ?? 0;
  const pinnedImages =
    variant.media.formats?.filter((format) => format.pinned).length ?? 0;

  const items = [
    t("funnel-flow.paid-social.launchpad.common.primary-text-count", {
      count: remainingAssetCount(countPayloads(variant, "primary_text")),
    }),
    t("funnel-flow.paid-social.launchpad.common.headline-count", {
      count: remainingAssetCount(countPayloads(variant, "headline")),
    }),
    t("funnel-flow.paid-social.launchpad.common.description-count", {
      count: remainingAssetCount(countPayloads(variant, "description")),
    }),
    t("funnel-flow.paid-social.launchpad.common.cta-count", {
      count: remainingAssetCount(countPayloads(variant, "cta")),
    }),
    t("funnel-flow.paid-social.launchpad.common.image-count", {
      count: totalImages - pinnedImages,
    }),
  ];

  return new Intl.ListFormat(locale.value, {
    style: "short",
    type: "unit",
  }).format(items);
}

const handleClose = () => {
  isOpen.value = false;
};
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="540"
    closeOnClickOutside
    closeButton
    useCustomClose
    @customClose="handleClose"
  >
    <div class="tw:px-6 tw:py-8">
      <div
        class="tw:mx-auto tw:mb-5 tw:flex tw:flex-col tw:items-center tw:gap-3 tw:text-center"
        style="max-width: 342px"
      >
        <img class="tw:h-[120px]" src="/images/celebrar-image.png" />

        <h2 class="tw:text-3xl tw:font-bold">
          {{
            $t(
              "funnel-flow.paid-social.launchpad.campaign-upload.success.title",
            )
          }}
        </h2>

        <p class="tw:font-medium tw:text-secondary">
          {{
            $t(
              "funnel-flow.paid-social.launchpad.campaign-upload.success.description",
              {
                campaignName:
                  preCheckStore.campaign?.name ||
                  $t(
                    "funnel-flow.paid-social.launchpad.campaign-upload.summary.campaign",
                  ),
              },
            )
          }}
        </p>
      </div>

      <div
        v-if="preCheckStore.isStandardMode"
        class="tw:mb-5 tw:flex tw:flex-col tw:gap-5"
      >
        <CardBase class="tw:divide-y tw:divide-gray-300">
          <div class="tw:px-6 tw:py-4 tw:font-medium">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.success.remaining-assets",
              )
            }}
          </div>

          <div
            v-for="creative in preCheckStore.creativesWithData"
            :key="creative.idx"
            class="tw:flex tw:flex-col tw:items-center tw:gap-4 tw:px-6 tw:py-4 tw:sm:flex-row"
          >
            <div class="tw:grow">
              <p class="tw:text-sm tw:font-semibold">{{ creative.name }}</p>

              <p class="tw:text-xs tw:text-secondary">
                {{ remainingAssetsSummary(creative.idx) }}
              </p>
            </div>

            <AdsLaunchpadDownloadAssetsButton :creativeId="creative.idx" />
          </div>
        </CardBase>

        <Alert type="info">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.success.setup-guide-title",
              )
            }}
          </template>

          <i18n-t
            keypath="funnel-flow.paid-social.launchpad.campaign-upload.success.setup-guide-description"
            tag="span"
          >
            <template #metaAdsManager>
              <!-- TODO: temporary Meta import-ads help article until Wizerlink provides the official setup-guide link -->
              <Link
                external
                href="https://www.facebook.com/business/help/232961787388181"
                underline
                color="info-dark"
              >
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.campaign-upload.success.meta-ads-manager",
                  )
                }}
              </Link>
            </template>
          </i18n-t>
        </Alert>
      </div>

      <div class="tw:flex tw:justify-center tw:gap-5">
        <Button
          type="button"
          variant="outlined"
          color="secondary"
          @click="handleClose"
          size="md"
        >
          {{
            $t(
              "funnel-flow.paid-social.launchpad.campaign-upload.success.back-to-dashboard",
            )
          }}
        </Button>

        <Button
          external
          :href="preCheckStore.metaUrl"
          @click="handleClose"
          size="md"
          icon="tabler:external-link"
        >
          {{
            $t(
              "funnel-flow.paid-social.launchpad.campaign-upload.success.open-in-meta-ads",
            )
          }}
        </Button>
      </div>
    </div>
  </Modal>
</template>
