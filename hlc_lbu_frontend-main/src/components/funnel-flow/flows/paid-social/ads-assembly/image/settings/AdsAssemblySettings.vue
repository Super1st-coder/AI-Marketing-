<script setup lang="ts">
import {
  InsufficientCreditsError,
  UnidentifiedError,
} from "@/services/common-errors";
import {
  creditsRefusalFromJob,
  videoCreditsErrorKey,
} from "@/composables/useVideoCredits";
import AdStructureApi, {
  isGenerateAdVariationsJobFinished,
} from "@/services/funnel-flow/paid-social/AdStructureApi";

const store = useFunnelPaidSocialAdsAssemblyStore();
const { t } = useI18n();

const isGenerating = ref(false);
const selectedVariations = ref<number>(1);
const generalErrorMessage = ref<string | undefined>(undefined);

// Luca Credits (Gate 2), same as the video flow: the low-balance alert above, and the
// "Add credits" window when a generation is refused for lack of credits
const { balance: creditsBalance, refresh: refreshCredits } = useVideoCredits();
const isAddCreditsOpen = ref(false);
// Luca Credits isn't released in production yet: it shows (and reads the balance) only where
// the video flow is on, so this screen, which production uses, stays as it was there
const showsCredits = IS_VIDEO_GENERATION_ENABLED_BY_DEFAULT;

// Create abort controller
const poolAbortController = ref<AbortController | undefined>(
  new AbortController(),
);

// Abort pooling when unmounting
onUnmounted(() => {
  poolAbortController.value?.abort();
});

async function handleGenerateVariations() {
  try {
    isGenerating.value = true;
    generalErrorMessage.value = undefined;

    if (!store.currentSet) {
      throw new UnidentifiedError();
    }

    // Start job to generate variants
    const response = await AdStructureApi.startGenerateAdVariationsJob({
      brand_id: store.brandId,
      campaign_id: store.campaignId,
      ad_set_id: store.currentSet.id,
      n_variants: selectedVariations.value,
    });

    // Start a pooling process to wait for the final response or error
    const jobId = response.data.job_id;
    const result = await pooling(
      async () => {
        const { data: response } =
          await AdStructureApi.getGenerateAdVariationsJobResult(jobId, {
            signal: poolAbortController.value?.signal,
          });

        return response;
      },
      (response) => isGenerateAdVariationsJobFinished(response),
      ADS_ASSEMBLY_GENERATE_AD_VARIATIONS_JOB_POLLING_INTERVAL_MS,
      { timeoutMs: ADS_ASSEMBLY_GENERATE_AD_VARIATIONS_JOB_TIMEOUT_MS },
    );

    // Refused by Luca Credits inside the job: handled below like a refused start
    const refusal = creditsRefusalFromJob(result);
    if (refusal) throw refusal;

    if (result.status === "FAILED") {
      generalErrorMessage.value = t(
        "funnel-flow.paid-social.ads.settings.errors.no-ads-generated",
      );
      return;
    }

    // The job was successfull, refetch the the whole ad
    await store.refetchCurrentAd();
    // It charged credits: keep the counter and the alert current
    if (showsCredits) await refreshCredits();

    // No ads were generated
    const foundAds = Object.values(store.ads).some(
      (ad) => ad.ad_channels.length > 0,
    );

    if (!foundAds) {
      // The images of every ad were refused for lack of credits (the job itself finishes)
      if (showsCredits && (creditsBalance.value?.available ?? 1) <= 0) {
        throw new InsufficientCreditsError();
      }
      generalErrorMessage.value = t(
        "funnel-flow.paid-social.ads.settings.errors.no-ads-generated",
      );
      return;
    }

    // Take the user to the next screen
    store.setScreen("refine");
  } catch (error: unknown) {
    console.error(error);

    // The pooling was aborted
    if ((error as any)?.name === "AbortError") {
      return;
    }

    // Out of credits / billing down get their own message, as in the video flow
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey && showsCredits) void refreshCredits();
    // Offer the way out, not just the error
    if (showsCredits && error instanceof InsufficientCreditsError)
      isAddCreditsOpen.value = true;
    generalErrorMessage.value = t(
      billingKey ??
        "funnel-flow.paid-social.ads.settings.errors.ai-generation-error",
    );
  } finally {
    isGenerating.value = false;
  }
}

const loadingTexts = computed(() => [
  t("funnel-flow.paid-social.ads.settings.loading-texts.computer-vision"),
  t("funnel-flow.paid-social.ads.settings.loading-texts.natural-language"),
  t(
    "funnel-flow.paid-social.ads.settings.loading-texts.generative-engine-model",
  ),
  t(
    "funnel-flow.paid-social.ads.settings.loading-texts.creative-similarity-score",
  ),
  t("funnel-flow.paid-social.ads.settings.loading-texts.ad-delivery-pipeline"),
  t("funnel-flow.paid-social.ads.settings.loading-texts.estimated-action-rate"),
  t("funnel-flow.paid-social.ads.settings.loading-texts.ad-quality-score"),
  t("funnel-flow.paid-social.ads.settings.loading-texts.social-graph"),
]);
</script>

<template>
  <template v-if="isGenerating">
    <div
      class="tw:mx-auto tw:flex tw:h-[calc(100vh-66px)] tw:max-w-[510px] tw:flex-col tw:items-center tw:justify-center"
    >
      <CircleLoaderDefault class="tw:mb-6" />

      <h2 class="tw:mb-3 tw:text-3xl tw:font-bold">
        <CyclingText :texts="loadingTexts" :interval="10 * SECOND_IN_MS" />
      </h2>

      <p class="tw:font-medium tw:text-secondary-text">
        {{ $t("funnel-flow.paid-social.ads.settings.loading-description") }}
      </p>
    </div>

    <ModalFormSaveAlert :isDirty="isGenerating" />
  </template>
  <template v-else>
    <FormStepLayout v-if="store.currentSet" as="div" :maxWidth="910">
      <template #stepper>
        <AdsAssemblyImageStepper />
      </template>

      <PageTitle
        helpButton
        helpVideoUrl="https://www.youtube.com/watch?v=r1462xlXJOQ"
      >
        {{
          $t("funnel-flow.paid-social.ads.settings.title", {
            adSetName: store.currentSet.name,
          })
        }}

        <template #description>
          {{ $t("funnel-flow.paid-social.ads.settings.description") }}
        </template>

        <template #after>
          <AdsAssemblyAbyssaleLinkButton />
        </template>
      </PageTitle>

      <AdsAssemblyVideoCreditAlert v-if="showsCredits" />

      <AdsAssemblySettingsCard icon="custom-rocket" iconVariant="info">
        <template #title>
          {{ $t("funnel-flow.paid-social.ads.settings.auto-assembly.title") }}
        </template>

        <template #description>
          {{
            $t("funnel-flow.paid-social.ads.settings.auto-assembly.description")
          }}
        </template>

        <div class="tw:grid tw:grid-cols-1 tw:gap-4">
          <AdsAssemblySettingsOption
            :value="1"
            v-model="selectedVariations"
            icon="tabler:box-multiple"
          >
            <template #title>
              {{
                $t(
                  "funnel-flow.paid-social.ads.settings.auto-assembly.option-1.title",
                )
              }}
            </template>

            <template #description>
              {{
                $t(
                  "funnel-flow.paid-social.ads.settings.auto-assembly.option-1.description",
                  { count: store.currentSet.ads.length },
                )
              }}
            </template>
          </AdsAssemblySettingsOption>

          <AdsAssemblySettingsOption
            :value="2"
            v-model="selectedVariations"
            icon="tabler:stack-2"
          >
            <template #title>
              {{
                $t(
                  "funnel-flow.paid-social.ads.settings.auto-assembly.option-2.title",
                )
              }}
            </template>

            <template #description>
              {{
                $t(
                  "funnel-flow.paid-social.ads.settings.auto-assembly.option-2.description",
                  {
                    generatedCount: store.currentSet.ads.length * 2,
                    selectedCount: store.currentSet.ads.length,
                  },
                )
              }}
            </template>
          </AdsAssemblySettingsOption>

          <AdsAssemblySettingsOption
            :value="3"
            v-model="selectedVariations"
            icon="tabler:bolt"
          >
            <template #title>
              {{
                $t(
                  "funnel-flow.paid-social.ads.settings.auto-assembly.option-3.title",
                )
              }}
            </template>

            <template #description>
              {{
                $t(
                  "funnel-flow.paid-social.ads.settings.auto-assembly.option-3.description",
                  { count: store.currentSet?.ads.length * 3 },
                )
              }}
            </template>
          </AdsAssemblySettingsOption>
        </div>

        <AdsAssemblyVideoAddCreditsModal
          v-if="showsCredits"
          v-model="isAddCreditsOpen"
        />

        <Alert v-if="generalErrorMessage" type="error" autoScroll>
          {{ generalErrorMessage }}
        </Alert>

        <Button
          leftIcon="custom:hi-luca"
          :uppercase="false"
          @click="handleGenerateVariations"
        >
          {{ $t("funnel-flow.paid-social.ads.settings.auto-assembly.button") }}
        </Button>
      </AdsAssemblySettingsCard>

      <AdsAssemblySettingsCard icon="custom-rocket" iconVariant="info">
        <template #title>
          {{ $t("funnel-flow.paid-social.ads.settings.manual-builder.title") }}
        </template>

        <template #description>
          {{
            $t(
              "funnel-flow.paid-social.ads.settings.manual-builder.description",
            )
          }}
        </template>

        <!-- Manual mode: skip generation and go straight to the refine step -->
        <Button
          color="secondary"
          variant="outlined"
          :uppercase="false"
          @click="store.setScreen('refine')"
        >
          {{ $t("funnel-flow.paid-social.ads.settings.manual-builder.button") }}
        </Button>
      </AdsAssemblySettingsCard>

      <template #actions>
        <WizardCardActions>
          <ButtonGoBack @click="store.setScreen('assetOrigin')" />
        </WizardCardActions>
      </template>
    </FormStepLayout>
  </template>
</template>
