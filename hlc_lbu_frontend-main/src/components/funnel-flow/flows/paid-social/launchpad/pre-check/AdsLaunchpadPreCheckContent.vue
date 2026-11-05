<script setup lang="ts">
import CardBase from "@/components/cards/base/CardBase.vue";

const props = defineProps<{
  step: "pre-check" | "summary";
}>();
const { t } = useI18n();

const { goBack } = useMultiStepFormContext();

const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

// Visual modals
// const incompatibleMediaTypesModalOpen = ref(false);
const invalidMediaSpecsModalOpen = ref(false);
const imageLimitModalOpen = ref(false);

// Text modals
const characterLimitExceededModalOpen = ref(false);
const duplicateTextDetectedModalOpen = ref(false);
const limitExceededPrimaryTextModalOpen = ref(false);
const limitExceededHeadlinesModalOpen = ref(false);
const limitExceededDescriptionModalOpen = ref(false);
const ctaNotSupportedModalOpen = ref(false);

// Track which creative is being edited in modals
const currentCreative = ref<CreativeWithData | undefined>(undefined);

// Delivery modals
// const limitExceededTotalAssetsModalOpen = ref(false);
const budgetBelowMinimumModalOpen = ref(false);
const urlVerificationFailedModalOpen = ref(false);
const targetingModalOpen = ref(false);

const campaignUploadModalOpen = ref(false);

// In standard mode, the ad set name is shown once on the group's parent card,
// so each accordion only needs the ad name as its title. In the other modes,
// there's no parent card, so the title is "{ad set} - {ad}" instead. The
// pre-check endpoint already returns the name in that format, but the
// published campaign endpoint only returns the ad set name, so the ad name is
// appended then
const getCreativeTitle = (creative: CreativeWithData) => {
  if (preCheckStore.isStandardMode) {
    return creative.adName;
  }

  if (creative.name.endsWith(` - ${creative.adName}`)) {
    return creative.name;
  }

  return `${creative.name} - ${creative.adName}`;
};

// The ad set name shown on the group's parent card (standard mode only). The
// pre-check endpoint returns it as `creative.name`, stripping the ad name
// suffix the published campaign endpoint appends to it
const getAdSetTitle = (creative: CreativeWithData) =>
  creative.name.endsWith(` - ${creative.adName}`)
    ? creative.name.slice(0, -` - ${creative.adName}`.length)
    : creative.name;

const getAudienceOfCreative = (creative: CreativeWithData) =>
  creative.audiences.find((channel) => channel.preferred_audience != null)
    ?.preferred_audience ?? undefined;

// In standard mode, the ads of each ad set are grouped inside a card. In the
// other modes, all the ads are displayed in a single list
const creativeGroups = computed(() => {
  const creatives = preCheckStore.creativesWithData;

  if (!preCheckStore.isStandardMode) {
    return [{ key: "all", creatives }];
  }

  const groups = new Map<number, CreativeWithData[]>();
  creatives.forEach((creative) => {
    const group = groups.get(creative.adset_id);
    if (group) {
      group.push(creative);
    } else {
      groups.set(creative.adset_id, [creative]);
    }
  });

  return Array.from(groups, ([adSetId, adSetCreatives]) => ({
    key: adSetId,
    creatives: adSetCreatives,
  }));
});

const handlePublishCampaign = () => {
  if (props.step === "pre-check") {
    campaignUploadModalOpen.value = true;
  }
};
</script>

<template>
  <FormStepLayout as="div">
    <!-- Horizontal Stepper -->
    <template #stepper>
      <AdsLaunchpadStepper />
    </template>

    <!-- Campaign header -->
    <AdsLaunchpadCampaignHeader
      v-if="preCheckStore.campaign"
      :campaign="preCheckStore.campaign"
    >
      <AdsLaunchpadCampaignHeaderPreCheck :campaign="preCheckStore.campaign" />

      <template v-if="step === 'summary' && preCheckStore.metaUrl" #actions>
        <Button
          external
          :href="preCheckStore.metaUrl"
          size="sm"
          icon="tabler:external-link"
          :shadow="false"
        >
          {{ $t("funnel-flow.paid-social.launchpad.common.view-in-meta-ads") }}
        </Button>
      </template>
    </AdsLaunchpadCampaignHeader>

    <AccordionList variant="card">
      <!-- Ad set card (standard mode only, otherwise it doesn't affect the layout) -->
      <component
        :is="preCheckStore.isStandardMode ? CardBase : 'div'"
        v-for="(group, groupIndex) in creativeGroups"
        :key="group.key"
        :class="
          preCheckStore.isStandardMode
            ? 'tw:flex tw:flex-col tw:gap-3 tw:p-4'
            : 'tw:contents'
        "
      >
        <!-- Ad set title and buttons (standard mode only) -->
        <div v-if="preCheckStore.isStandardMode && group.creatives[0]">
          <h3 class="tw:mb-2 tw:text-xl tw:font-bold">
            {{ getAdSetTitle(group.creatives[0]) }}
          </h3>

          <div class="tw:flex tw:flex-wrap tw:gap-4">
            <CreativeAngleButton
              :creativeAngle="group.creatives[0].experiment"
            />

            <AudienceButton
              :audience="getAudienceOfCreative(group.creatives[0])"
            />
          </div>
        </div>

        <!-- Creative accordion -->
        <Accordion
          v-for="(creative, index) in group.creatives"
          :key="creative.idx"
          :openByDefault="groupIndex === 0 && index === 0"
        >
          <template #title>
            <span class="tw:text-xl tw:font-bold">
              {{ getCreativeTitle(creative) }}
            </span>

            <Chip v-if="step === 'summary'" color="success" variant="label">
              {{ $t("funnel-flow.paid-social.launchpad.pre-check.published") }}
            </Chip>

            <Chip
              v-else
              :color="
                preCheckStore.getErrorCount(creative.idx) > 0
                  ? 'warning'
                  : 'success'
              "
              variant="label"
            >
              {{
                preCheckStore.getErrorCount(creative.idx) > 0
                  ? t(
                      "funnel-flow.paid-social.launchpad.pre-check.issues-found",
                      { count: preCheckStore.getErrorCount(creative.idx) },
                    )
                  : t(
                      "funnel-flow.paid-social.launchpad.pre-check.ready-to-publish",
                    )
              }}
            </Chip>
          </template>

          <template
            v-if="step === 'summary' && preCheckStore.isStandardMode"
            #actions
          >
            <AdsLaunchpadDownloadAssetsButton :creativeId="creative.idx" />
          </template>

          <div class="tw:flex tw:flex-col tw:gap-5">
            <!-- Buttons (non-standard mode only, otherwise they're shown once
            on the ad set's parent card) -->
            <div
              v-if="!preCheckStore.isStandardMode"
              class="tw:flex tw:flex-wrap tw:gap-4"
            >
              <CreativeAngleButton :creativeAngle="creative.experiment" />

              <AudienceButton :audience="getAudienceOfCreative(creative)" />
            </div>

            <!-- Validation info cards -->
            <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:lg:grid-cols-3">
              <AdsLaunchpadPreCheckValidationCard
                :title="
                  t(
                    'funnel-flow.paid-social.launchpad.pre-check.visual-assets.title',
                  )
                "
                icon="tabler:photo"
              >
                <!-- <AdsLaunchpadPreCheckValidationCardSection
                title="Media Types"
                :error="preCheckStore.getMediaTypesError(creative.idx)"
                @click="incompatibleMediaTypesModalOpen = true"
              /> -->

                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.visual-assets.media-specs',
                    )
                  "
                  :error="preCheckStore.getMediaSpecsError(creative.idx)"
                  @click="
                    currentCreative = creative;
                    invalidMediaSpecsModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />

                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.visual-assets.image-count',
                    )
                  "
                  :error="preCheckStore.getImageCountError(creative.idx)"
                  @click="
                    currentCreative = creative;
                    imageLimitModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
              </AdsLaunchpadPreCheckValidationCard>

              <AdsLaunchpadPreCheckValidationCard
                :title="
                  t(
                    'funnel-flow.paid-social.launchpad.pre-check.text-assets.title',
                  )
                "
                icon="tabler:file-text"
              >
                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.text-assets.text-length',
                    )
                  "
                  :error="preCheckStore.getTextLengthError(creative.idx)"
                  @click="
                    currentCreative = creative;
                    characterLimitExceededModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
                <AdsLaunchpadPreCheckValidationCardSection
                  v-if="!preCheckStore.isStandardMode"
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.text-assets.duplicate-check',
                    )
                  "
                  :error="preCheckStore.getDuplicateCheckError(creative.idx)"
                  @click="
                    currentCreative = creative;
                    duplicateTextDetectedModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.text-assets.primary-text-count',
                    )
                  "
                  :error="preCheckStore.getPrimaryTextCountError(creative.idx)"
                  @click="
                    currentCreative = creative;
                    limitExceededPrimaryTextModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.text-assets.headlines-count',
                    )
                  "
                  :error="preCheckStore.getHeadlinesCountError(creative.idx)"
                  @click="
                    currentCreative = creative;
                    limitExceededHeadlinesModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.text-assets.description-count',
                    )
                  "
                  :error="preCheckStore.getDescriptionCountError(creative.idx)"
                  @click="
                    currentCreative = creative;
                    limitExceededDescriptionModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.text-assets.cta',
                    )
                  "
                  :error="preCheckStore.getCtaError(creative.idx)"
                  @click="
                    currentCreative = creative;
                    ctaNotSupportedModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
              </AdsLaunchpadPreCheckValidationCard>

              <AdsLaunchpadPreCheckValidationCard
                :title="
                  t(
                    'funnel-flow.paid-social.launchpad.pre-check.settings-delivery.title',
                  )
                "
                icon="tabler:settings"
              >
                <!-- <AdsLaunchpadPreCheckValidationCardSection
                title="Total Assets"
                error="Exceeds 30"
                @click="limitExceededTotalAssetsModalOpen = true"
              /> -->
                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.settings-delivery.minimum-budget',
                    )
                  "
                  :error="preCheckStore.getBudgetError(creative.idx)"
                  editable
                  @click="
                    currentCreative = creative;
                    budgetBelowMinimumModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.settings-delivery.proposed-url',
                    )
                  "
                  :error="preCheckStore.getUrlError(creative.idx)"
                  editable
                  @click="
                    currentCreative = creative;
                    urlVerificationFailedModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
                <AdsLaunchpadPreCheckValidationCardSection
                  :title="
                    t(
                      'funnel-flow.paid-social.launchpad.pre-check.settings-delivery.geo-targeting',
                    )
                  "
                  :error="preCheckStore.getTargetingError(creative.idx)"
                  editable
                  @click="
                    currentCreative = creative;
                    targetingModalOpen = true;
                  "
                  :readonly="step === 'summary'"
                />
              </AdsLaunchpadPreCheckValidationCard>
            </div>
          </div>
        </Accordion>
      </component>
    </AccordionList>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />

        <Button
          v-if="step === 'pre-check'"
          @click="handlePublishCampaign"
          :disabled="preCheckStore.hasErrorsInAnyAd"
        >
          {{
            t("funnel-flow.paid-social.launchpad.pre-check.publish-campaign")
          }}
        </Button>
      </WizardCardActions>
    </template>

    <!-- Visual modals -->
    <!-- <AdsLaunchpadIncompatibleMediaTypesModal
      v-if="incompatibleMediaTypesModalOpen"
      v-model="incompatibleMediaTypesModalOpen"
    /> -->
    <AdsLaunchpadInvalidMediaSpecsModal
      v-if="currentCreative && invalidMediaSpecsModalOpen"
      v-model="invalidMediaSpecsModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />
    <AdsLaunchpadImageLimitModal
      v-if="currentCreative && imageLimitModalOpen"
      v-model="imageLimitModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />

    <!-- Text modals -->
    <AdsLaunchpadCharacterLimitExceededModal
      v-if="currentCreative && characterLimitExceededModalOpen"
      v-model="characterLimitExceededModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />
    <AdsLaunchpadDuplicateTextDetectedModal
      v-if="currentCreative && duplicateTextDetectedModalOpen"
      v-model="duplicateTextDetectedModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />
    <AdsLaunchpadLimitExceededPrimaryTextModal
      v-if="currentCreative && limitExceededPrimaryTextModalOpen"
      v-model="limitExceededPrimaryTextModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />
    <AdsLaunchpadLimitExceededHeadlinesModal
      v-if="currentCreative && limitExceededHeadlinesModalOpen"
      v-model="limitExceededHeadlinesModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />
    <AdsLaunchpadLimitExceededDescriptionModal
      v-if="currentCreative && limitExceededDescriptionModalOpen"
      v-model="limitExceededDescriptionModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />
    <AdsLaunchpadCtaNotSupportedModal
      v-if="currentCreative && ctaNotSupportedModalOpen"
      v-model="ctaNotSupportedModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />

    <!-- Delivery modals -->
    <!-- <AdsLaunchpadLimitExceededTotalAssetsModal
      v-if="limitExceededTotalAssetsModalOpen"
      v-model="limitExceededTotalAssetsModalOpen"
    /> -->
    <AdsLaunchpadBudgetBelowMinimumModal
      v-if="currentCreative && budgetBelowMinimumModalOpen"
      v-model="budgetBelowMinimumModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />
    <AdsLaunchpadUrlVerificationFailedModal
      v-if="currentCreative && urlVerificationFailedModalOpen"
      v-model="urlVerificationFailedModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />
    <AdsLaunchpadTargetingModal
      v-if="currentCreative && targetingModalOpen"
      v-model="targetingModalOpen"
      :creativeId="currentCreative.idx"
      :readonly="step === 'summary'"
    />

    <AdsLaunchpadCampaignUploadModal
      v-if="campaignUploadModalOpen"
      v-model="campaignUploadModalOpen"
    />
  </FormStepLayout>
</template>
