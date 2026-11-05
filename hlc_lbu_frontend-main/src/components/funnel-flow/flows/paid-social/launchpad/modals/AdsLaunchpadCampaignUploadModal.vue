<script setup lang="ts">
import ChannelConnections, {
  LaunchPublishTaskValue,
} from "@/services/funnel-flow/ChannelConnections";
import { UnidentifiedError } from "@/services/common-errors";
import UtilsApi from "@/services/UtilsApi";
import { pooling } from "@/utils/pooling";

const { t } = useI18n();

const isOpen = defineModel<boolean>({ required: true });
const checkbox = ref<boolean>();

const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

const { goNext } = useMultiStepFormContext();

const currentScreen = ref<"confirm" | "uploading">("confirm");
const generalErrorTitle = ref<string | undefined>(undefined);
const generalErrorMessage = ref<string | undefined>(undefined);

const campaignObjective = computed(() => {
  const objective =
    preCheckStore.preCheckResponse?.data.campaign.objective ?? "";
  return objective
    ? t(`meta-ads.objectives.${objective}.title`, objective)
    : objective;
});

// Only set for Leads optimized for conversions on the website
const conversionEvent = computed(() => {
  const event = preCheckStore.launchConfiguration?.conversion_event;
  return event ? t(`meta-ads.conversion-events.${event}.title`, event) : "";
});

const handleCancel = () => {
  isOpen.value = false;
  generalErrorTitle.value = undefined;
  generalErrorMessage.value = undefined;
  currentScreen.value = "confirm";
};

const POLL_INTERVAL_MS = 4000;
const POLL_MAX_ATTEMPTS = 480;

const handleConfirm = async () => {
  if (currentScreen.value !== "confirm") {
    return;
  }

  generalErrorTitle.value = undefined;
  generalErrorMessage.value = undefined;
  currentScreen.value = "uploading";

  try {
    const response = await ChannelConnections.publishLaunchToMeta({
      brand_id: preCheckStore.brandId,
      campaign_id: preCheckStore.campaignId,
      creatives: preCheckStore.creativesWithData.map((c) => ({
        adset_id: c.adset_id,
        ad_id: c.ad_id,
        adchannel_id: c.adchannel_id,
      })),
    });

    const jobId = response.data.job_id;
    const result = await pooling(
      () => UtilsApi.getTaskResult<LaunchPublishTaskValue>(jobId),
      (res) => (res?.data?.ready ?? false) === true,
      POLL_INTERVAL_MS,
      { maxAttempts: POLL_MAX_ATTEMPTS },
    );

    // Catch error in the task result
    if (result.data.value && result.data.value.ok === 0) {
      const title =
        result.data.value.message?.text?.error?.error_user_title ??
        t(
          "funnel-flow.paid-social.launchpad.campaign-upload.errors.upload-failed",
        );
      const message =
        result.data.value.message?.text?.error?.error_user_msg ??
        t(
          "funnel-flow.paid-social.launchpad.campaign-upload.errors.could-not-upload",
        );

      currentScreen.value = "confirm";
      generalErrorTitle.value = title;
      generalErrorMessage.value = message;
      return;
    }

    if (result.data.value?.data) {
      // Success
      preCheckStore.metaUrl = result.data.value.data.meta_url;
      preCheckStore.isPublished = true;
      preCheckStore.campaignUploadSuccessModalOpen = true;
      isOpen.value = false;
      await nextTick();
      goNext();
    } else {
      throw new UnidentifiedError();
    }
  } catch (e: unknown) {
    console.error(e);

    currentScreen.value = "confirm";
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.launchpad.campaign-upload.errors.unexpected",
    );
  }
};

const totalAssetsCount = computed(() => {
  return preCheckStore.creativesWithData.reduce((sum, creative) => {
    const bodies = preCheckStore.getSelectedBodies(creative.idx).length;
    const titles = preCheckStore.getSelectedTitles(creative.idx).length;
    const descriptions = preCheckStore.getSelectedDescriptions(
      creative.idx,
    ).length;
    const images = preCheckStore.getSelectedImages(creative.idx).length;
    const ctas = preCheckStore.getSelectedCTAs(creative.idx).length ?? 0;
    return sum + bodies + titles + descriptions + images + ctas;
  }, 0);
});
</script>

<template>
  <Modal
    v-if="currentScreen === 'confirm'"
    v-model="isOpen"
    :maxWidth="600"
    closeButton
    useCustomClose
    @customClose="handleCancel"
  >
    <ModalHeader>
      {{
        $t("funnel-flow.paid-social.launchpad.campaign-upload.confirm.title")
      }}

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.campaign-upload.confirm.description",
          )
        }}
      </template>
    </ModalHeader>

    <ModalBody class="tw:grid tw:grid-cols-1 tw:gap-5">
      <CardBase class="tw:grid tw:grid-cols-1 tw:gap-6 tw:p-6">
        <AdsLaunchpadCampaignUploadModalSection>
          <template #label>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.summary.campaign-details",
              )
            }}
          </template>
        </AdsLaunchpadCampaignUploadModalSection>

        <AdsLaunchpadCampaignUploadModalSection>
          <template #label>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.summary.name",
              )
            }}
          </template>

          {{ preCheckStore.campaign?.name }}
        </AdsLaunchpadCampaignUploadModalSection>

        <AdsLaunchpadCampaignUploadModalSection>
          <template #label>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.summary.goal",
              )
            }}
          </template>

          {{ campaignObjective }}
        </AdsLaunchpadCampaignUploadModalSection>

        <AdsLaunchpadCampaignUploadModalSection v-if="conversionEvent">
          <template #label>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.summary.conversion-event",
              )
            }}
          </template>

          {{ conversionEvent }}
        </AdsLaunchpadCampaignUploadModalSection>

        <AdsLaunchpadCampaignUploadModalSection>
          <template #label>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.summary.billing-event",
              )
            }}
          </template>

          AUCTION
        </AdsLaunchpadCampaignUploadModalSection>

        <AdsLaunchpadCampaignUploadModalSection>
          <template #label>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.summary.buying-type",
              )
            }}
          </template>

          AUCTION
        </AdsLaunchpadCampaignUploadModalSection>

        <Separator />

        <AdsLaunchpadCampaignUploadModalSection mode="col">
          <template #label>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.campaign-upload.structure.title",
              )
            }}
          </template>

          <div class="tw:flex tw:items-center tw:gap-1.5">
            <span>
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.campaign-upload.structure.one-campaign",
                )
              }}
            </span>

            <Icon icon="tabler-chevron-right" class="tw:text-xl" />

            <span>
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.campaign-upload.structure.ad-sets",
                  { count: preCheckStore.creativesWithData.length },
                )
              }}
            </span>

            <Icon icon="tabler-chevron-right" class="tw:text-xl" />

            <span>
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.campaign-upload.structure.assets",
                  { count: totalAssetsCount },
                )
              }}
            </span>
          </div>
        </AdsLaunchpadCampaignUploadModalSection>
      </CardBase>

      <Alert type="warning" autoScroll>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.campaign-upload.warning-message",
          )
        }}
      </Alert>

      <FieldBaseCheckbox
        v-model="checkbox"
        name="understand"
        :label="
          $t(
            'funnel-flow.paid-social.launchpad.campaign-upload.confirmation-checkbox',
          )
        "
        class="tw:text-sm"
      />

      <Alert v-if="generalErrorMessage" type="error" autoScroll>
        <template v-if="generalErrorTitle" #title>
          {{ generalErrorTitle }}
        </template>

        {{ generalErrorMessage }}
      </Alert>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        variant="outlined"
        color="secondary"
        @click="handleCancel"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button type="button" @click="handleConfirm" :disabled="!checkbox">
        {{
          $t(
            "funnel-flow.paid-social.launchpad.campaign-upload.actions.upload-to-meta",
          )
        }}
      </Button>
    </ModalFooter>
  </Modal>

  <Modal
    v-else-if="currentScreen === 'uploading'"
    v-model="isOpen"
    :maxWidth="500"
    :closeButton="false"
    :closeOnClickOutside="false"
    fallbackFocusToForeground
  >
    <div class="tw:flex tw:flex-col tw:items-center tw:gap-3 tw:px-6 tw:py-8">
      <CircleLoaderDefault class="tw:text-[44px]" />

      <h3 class="tw:text-center tw:text-3xl tw:font-bold">
        {{
          $t(
            "funnel-flow.paid-social.launchpad.campaign-upload.actions.uploading-campaign",
          )
        }}
      </h3>

      <p class="tw:text-center tw:font-medium tw:text-secondary">
        {{
          $t(
            "funnel-flow.paid-social.launchpad.campaign-upload.actions.uploading-hint",
          )
        }}
      </p>
    </div>
  </Modal>
</template>
