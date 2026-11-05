<script setup lang="ts">
import VideoApi, {
  VideoDraft,
} from "@/services/funnel-flow/paid-social/VideoApi";
import {
  GenerationTakingTooLongError,
  getJobShotCounts,
  isGenerationOutcomeUnknown,
  watchVideoGenerationJob,
} from "../videoGenerationJob";
import AdsAssemblyVideoScriptsVariantPanel from "./AdsAssemblyVideoScriptsVariantPanel.vue";
import { VideoScriptVariantReviewState } from "./AdsAssemblyVideoScriptsReviewModal.vue";
import { VideoContentOptions } from "@/stores/funnel-flow/paid-social/FunnelPaidSocialAdsAssemblyStore";

const store = useFunnelPaidSocialAdsAssemblyStore();
const { t } = useI18n();
const { refresh: refreshCredits } = useVideoCredits();

const variants = computed(() =>
  Object.values(store.currentAd?.draft.variants ?? {}),
);

const initialTab = variants.value[0]?.variant_id;
const currentTab = ref<string | undefined>(initialTab);

// Shared by saving and storyboard generation, since only one can run at a time
const generalErrorMessage = ref<string>();

// The reviewed flags are saved per ad-channel row. A variant without one
// (drafts saved before the rows existed) only keeps it until the page is left
const rowIds = variants.value
  .map((variant) => store.getVideoVariantRowId(variant.variant_id))
  .filter((rowId) => rowId !== undefined);

const pendingRowIds = rowIds.length
  ? (
      await VideoApi.getVariantReviewStatus({
        variant_ids: rowIds,
        stage: "scripts",
      })
    ).pending
  : [];

const variantStates = ref<Record<string, VideoScriptVariantReviewState>>(
  Object.fromEntries(
    variants.value.map((variant) => {
      const rowId = store.getVideoVariantRowId(variant.variant_id);

      return [
        variant.variant_id,
        {
          reviewed: rowId !== undefined && !pendingRowIds.includes(rowId),
          dirty: false,
        },
      ];
    }),
  ),
);

// Only matters after a reload, so the callers don't wait for it. If saving
// fails, the variant still counts as reviewed until then
async function saveReviewedFlag(variantId: string) {
  const rowId = store.getVideoVariantRowId(variantId);
  if (rowId === undefined) return;

  try {
    const response = await VideoApi.markVariantReviewed({
      variant_id: rowId,
      stage: "scripts",
    });

    if (!response.saved) {
      console.error("The reviewed flag wasn't saved:", response);
    }
  } catch (error) {
    console.error("Failed to save the reviewed flag:", error);
  }
}

// A variant counts as reviewed as soon as its tab is opened. The previous
// panel unmounts, which discards any unsaved changes it had
watch(
  currentTab,
  (variantId, previousVariantId) => {
    if (!variantId) return;

    // Saved only the first time, the backend already has it after that
    if (!variantStates.value[variantId].reviewed) {
      void saveReviewedFlag(variantId);
    }

    variantStates.value[variantId].reviewed = true;

    if (previousVariantId) {
      variantStates.value[previousVariantId].dirty = false;
    }

    generalErrorMessage.value = undefined;
  },
  { immediate: true },
);

function isVariantPending(variantId: string) {
  const state = variantStates.value[variantId];
  return !state.reviewed || state.dirty;
}

const hasPendingVariants = computed(() =>
  variants.value.some((variant) => isVariantPending(variant.variant_id)),
);

const panelRefs =
  useTemplateRef<InstanceType<typeof AdsAssemblyVideoScriptsVariantPanel>[]>(
    "panelRefs",
  );

const savingVariantId = ref<string | null>(null);
const isGeneratingStoryboard = ref(false);
const isBusy = computed(
  () => savingVariantId.value !== null || isGeneratingStoryboard.value,
);

const isSaveModalOpen = ref(false);
const skipSaveModal = useLocalStorage<boolean>(
  "dontShowAgain.ads-assembly-video-scripts-save",
  false,
);
const variantToSave = ref<string>();

// What saving an edit costs: it re-scores the variant, which is charged in Luca Credits
// (HL-2739). Shown on the Save button and in the window before it, and the charge is
// capped at this + 10%. Fetched for the open variant; undefined while unknown
const rescoreCosts = ref<Record<string, number | undefined>>({});

async function loadRescoreCost(variantId: string | undefined) {
  const variant = variants.value.find((item) => item.variant_id === variantId);
  if (!variant || rescoreCosts.value[variant.variant_id] !== undefined) return;
  try {
    const estimate = await VideoApi.estimateVariants(
      [variant],
      store.currentAd?.draft.settings?.production_mode ?? "FULL_VIDEO",
      store.currentAd?.draft.settings?.model ?? null,
      store.currentSet?.id ?? null,
      null,
      store.currentAd?.ad_id ?? null,
    );
    if (estimate.rescore?.priced) {
      rescoreCosts.value = {
        ...rescoreCosts.value,
        [variant.variant_id]: estimate.rescore.lucas,
      };
    }
  } catch (error) {
    // Not blocking: without a price the button and the window just don't show one
    console.error("Failed to estimate the re-scoring cost:", error);
  }
}

watch(currentTab, loadRescoreCost, { immediate: true });

async function saveVariant(variantId: string) {
  savingVariantId.value = variantId;
  generalErrorMessage.value = undefined;

  try {
    // Refs in a v-for aren't guaranteed to follow the source order
    const panel = panelRefs.value?.find(
      (panel) => panel.$props.variant.variant_id === variantId,
    );

    await panel?.save();
  } catch (error) {
    console.error("Failed to save video script:", error);
    // Out of credits, video limit, billing down... get their own message
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    generalErrorMessage.value = t(
      billingKey ??
        "funnel-flow.paid-social.ads.video.scripts.errors.save-failed",
    );
  } finally {
    savingVariantId.value = null;
  }
}

// Moves to the variant first so validation errors are visible if saving fails
function handleSave(variantId: string) {
  currentTab.value = variantId;

  if (skipSaveModal.value) {
    saveVariant(variantId);
    return;
  }

  variantToSave.value = variantId;
  isSaveModalOpen.value = true;
}

async function handleConfirmSave() {
  if (variantToSave.value) {
    await saveVariant(variantToSave.value);
  }
}

const isReviewModalOpen = ref(false);
const isDiversityMatrixModalOpen = ref(false);

async function handleReview(variantId: string) {
  // Goes through the save lock like a tab click, so unsaved changes aren't
  // discarded without asking
  if ((await useSaveLockingStore().execute()) === "cancel") return;

  currentTab.value = variantId;
}

// Scripts Only asks which optional steps (storyboard, voiceover) to add before
// moving on
const isContentReadyModalOpen = ref(false);
const isScriptsOnly = computed(
  () => store.currentAd?.draft.settings.production_mode === "SCRIPTS_ONLY",
);

// What "Generate Storyboard" charges: one frame per shot of every variant, priced as the step
// charges it. Shown on the button, like Continue in Settings, since outside Scripts Only no
// window comes before the charge (Marco, 2026-11-03: the user pays the price they were shown).
// Scripts Only prices it in the "Is the content ready?" window instead. `undefined` while
// loading or unpriced, and then the button can't charge
const storyboardCost = ref<number>();
const isPricingStoryboard = ref(false);
// Only the latest request sets the price: an older one can answer after a newer one
let storyboardPriceRequest = 0;

async function loadStoryboardCost() {
  const request = ++storyboardPriceRequest;
  storyboardCost.value = undefined;
  isPricingStoryboard.value = false;
  if (isScriptsOnly.value || !variants.value.length) return;

  isPricingStoryboard.value = true;
  try {
    const estimate = await VideoApi.estimateVariants(
      variants.value,
      store.currentAd?.draft.settings?.production_mode ?? "FULL_VIDEO",
      store.currentAd?.draft.settings?.model ?? null,
      null,
      null,
      store.currentAd?.ad_id ?? null,
    );
    const cost = estimate.storyboard;
    if (request !== storyboardPriceRequest) return;
    if (cost.priced && cost.applies) storyboardCost.value = cost.lucas;
  } catch (error) {
    console.error("Failed to estimate the storyboard cost:", error);
  } finally {
    if (request === storyboardPriceRequest) isPricingStoryboard.value = false;
  }
}

// The price follows the shots: saving an edit can add or remove one
watch(
  () => [
    isScriptsOnly.value,
    store.currentAd?.draft.settings?.model,
    variants.value.map((variant) => variant.shots.length).join(),
  ],
  loadStoryboardCost,
  { immediate: true },
);

function handleGenerateStoryboard() {
  if (hasPendingVariants.value) {
    isReviewModalOpen.value = true;
    return;
  }

  if (isScriptsOnly.value) {
    isContentReadyModalOpen.value = true;
    return;
  }

  generateAndContinue();
}

function handleConfirmContentReady(options: VideoContentOptions) {
  generateAndContinue(options);
}

// Read when continuing, since the "Is the content ready?" modal can change it
function isStoryboardNext() {
  const screens = store.currentVideoScreens;
  return screens[screens.indexOf("videoScripts") + 1] === "videoStoryboard";
}

// Shows the loading screen instead of the scripts while the frames generate.
// Only for the storyboard: Scripts Only without one moves on right away. On an
// error the scripts come back with the error
const isShowingStoryboardLoading = ref(false);

// The job of the storyboard being generated, for its progress
const storyboardJob = shallowRef<ReturnType<typeof watchVideoGenerationJob>>();
// One frame per script shot. Shown as "0 of N" until the job is found, so the
// progress doesn't pop in a few seconds later
const storyboardTotalShots = ref(0);
const storyboardShots = computed(() => {
  const job = storyboardJob.value?.progress.value;
  return job
    ? getJobShotCounts(job)
    : { total: storyboardTotalShots.value, ready: 0, failed: 0 };
});
// Failed frames count as done, so it gets to 100%
const storyboardPercentage = computed(() => {
  const { total, ready, failed } = storyboardShots.value;
  return total ? Math.round(((ready + failed) / total) * 100) : 0;
});

// Every frame saved in the draft, to tell the new ones from them
function getFrameKeys(draft: VideoDraft) {
  return new Set(
    Object.values(draft.variants).flatMap((variant) =>
      (variant.frames ?? []).map(
        (frame) => frame.storage_key ?? frame.image_url,
      ),
    ),
  );
}

async function generateAndContinue(options?: VideoContentOptions) {
  const currentAd = store.currentAd;
  if (!currentAd || !store.currentSet) return;

  isGeneratingStoryboard.value = true;
  generalErrorMessage.value = undefined;

  try {
    // Saves the choice of the "Is the content ready?" modal, which enables the
    // Storyboard and Voiceover steps of Scripts Only. The refetch makes the
    // steps below see it
    if (options) {
      await VideoApi.saveDraft({ ad_id: currentAd.ad_id, settings: options });
      await store.refetchCurrentAd();
    }

    if (isStoryboardNext()) {
      // Read once: the generation can take long, and the user can open
      // another ad meanwhile, which changes `variants`
      const generatedVariants = variants.value;
      const previousFrameKeys = getFrameKeys(currentAd.draft);

      storyboardTotalShots.value = generatedVariants.reduce(
        (total, variant) => total + variant.shots.length,
        0,
      );
      isShowingStoryboardLoading.value = true;

      const job = watchVideoGenerationJob({
        adId: currentAd.ad_id,
        step: "storyboard",
        previousJobId: currentAd.draft.jobs?.storyboard,
      });
      storyboardJob.value = job;

      try {
        await VideoApi.generateStoryboard({
          id_adset: store.currentSet.id,
          ad_index: store.currentAdIndex,
          id_ad: currentAd.ad_id,
          brand_id: String(store.brandId),
          variants: generatedVariants,
          base_image_url: null,
          visual_directions: {},
        });
      } catch (error) {
        if (!isGenerationOutcomeUnknown(error)) throw error;

        // The backend keeps generating and saves the frames to the draft by
        // itself, so it goes on once they're there, as if it had answered
        await job.waitForResult((draft) =>
          [...getFrameKeys(draft)].some((key) => !previousFrameKeys.has(key)),
        );
      } finally {
        job.stop();
      }

      // Storyboard frames are charged in Luca Credits
      void refreshCredits();

      // The frames were generated without the visual directions applied
      // before, so they are cleared.
      const variantsWithDirection = generatedVariants.filter(
        (variant) => variant.visual_direction,
      );
      if (variantsWithDirection.length) {
        await VideoApi.saveDraft({
          ad_id: currentAd.ad_id,
          variants: Object.fromEntries(
            variantsWithDirection.map((variant) => [
              variant.variant_id,
              { visual_direction: "" },
            ]),
          ),
        });
      }

      // Load the draft the backend saved the frames to
      await store.refetchSingleAd(currentAd.ad_id);
    } else {
      // The backend only saves the step when it generates something, so it
      // is saved here for the step that comes next
      await VideoApi.saveDraft({
        ad_id: currentAd.ad_id,
        current_step: options?.voiceover_enabled ? "voiceover" : "video",
      });
      await store.refetchCurrentAd();
    }

    // Only moves on if the user is still on this ad
    if (store.currentAd?.ad_id === currentAd.ad_id) {
      store.setNextVideoScreen("videoScripts");
    }
  } catch (error) {
    console.error("Failed to generate storyboard:", error);
    // Out of credits, video limit, billing down... get their own message
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    generalErrorMessage.value = t(
      billingKey ??
        (error instanceof GenerationTakingTooLongError
          ? "funnel-flow.paid-social.ads.video.generating.errors.taking-too-long"
          : "funnel-flow.paid-social.ads.video.scripts.errors.storyboard-generation-failed"),
    );
  } finally {
    isGeneratingStoryboard.value = false;
    isShowingStoryboardLoading.value = false;
    storyboardJob.value = undefined;
  }
}
</script>

<template>
  <!-- No stepper while generating -->
  <AdsAssemblyVideoGenerating
    v-if="isShowingStoryboardLoading"
    :percentage="storyboardPercentage"
  >
    <template #title>
      {{ $t("funnel-flow.paid-social.ads.video.generating.storyboard.title") }}
    </template>

    <template #subtitle>
      {{
        $t("funnel-flow.paid-social.ads.video.generating.storyboard.subtitle", {
          campaign: store.campaign.name,
        })
      }}
    </template>

    <template #progress>
      {{
        $t(
          storyboardShots.failed
            ? "funnel-flow.paid-social.ads.video.generating.storyboard.progress-with-failures"
            : "funnel-flow.paid-social.ads.video.generating.storyboard.progress",
          storyboardShots,
        )
      }}
    </template>
  </AdsAssemblyVideoGenerating>

  <FormStepLayout v-else as="div" maxWidth="auto">
    <template #stepper>
      <AdsAssemblyVideoStepper />
    </template>

    <template #custom>
      <div class="tw:flex tw:h-full tw:flex-col tw:gap-6 tw:pt-6">
        <Container :maxWidth="910">
          <!-- TODO: add help video URL later -->
          <PageTitle helpButton>
            {{ $t("funnel-flow.paid-social.ads.video.scripts.title") }}

            <template #description>
              {{ $t("funnel-flow.paid-social.ads.video.scripts.description") }}
            </template>

            <template #after>
              <Button
                variant="outlined"
                color="secondary"
                leftIcon="tabler:grid-dots"
                type="button"
                @click="isDiversityMatrixModalOpen = true"
              >
                {{
                  $t(
                    "funnel-flow.paid-social.ads.video.diversity-matrix.button",
                  )
                }}
              </Button>
            </template>
          </PageTitle>

          <AdsAssemblyVideoCreditAlert class="tw:mt-4" />
        </Container>

        <Tabs
          v-model="currentTab"
          class="tw:flex tw:grow tw:flex-col"
          variant="buttonGroup"
          size="lg"
        >
          <Container :maxWidth="910">
            <TabsList>
              <Tab
                v-for="(variant, index) in variants"
                :key="variant.variant_id"
                :value="variant.variant_id"
                :icon="
                  isVariantPending(variant.variant_id)
                    ? undefined
                    : 'tabler:circle-check'
                "
                iconClass="tw:text-success"
                :hasAlert="isVariantPending(variant.variant_id)"
                class="tw:grow tw:basis-0"
              >
                {{
                  $t("funnel-flow.paid-social.ads.video.variant-tab", {
                    number: index + 1,
                  })
                }}
              </Tab>
            </TabsList>
          </Container>

          <TabPanel
            v-for="variant in variants"
            :key="variant.variant_id"
            :value="variant.variant_id"
            class="tw:flex tw:grow tw:flex-col"
          >
            <AdsAssemblyVideoScriptsVariantPanel
              ref="panelRefs"
              v-model:dirty="variantStates[variant.variant_id].dirty"
              class="tw:mt-5"
              :variant="variant"
              :isSaving="savingVariantId === variant.variant_id"
              :isGeneratingStoryboard="isGeneratingStoryboard"
              :isBusy="isBusy"
              :errorMessage="generalErrorMessage"
              :rescoreCost="rescoreCosts[variant.variant_id]"
              :storyboardCost="isScriptsOnly ? undefined : storyboardCost"
              :isStoryboardPriceRequired="!isScriptsOnly"
              :isPricingStoryboard="isPricingStoryboard"
              @save="handleSave(variant.variant_id)"
              @generateStoryboard="handleGenerateStoryboard"
            />
          </TabPanel>
        </Tabs>
      </div>

      <AdsAssemblyVideoScriptsSaveModal
        v-if="isSaveModalOpen"
        v-model="isSaveModalOpen"
        v-model:dontShowAgain="skipSaveModal"
        :cost="variantToSave ? rescoreCosts[variantToSave] : undefined"
        :saveFn="handleConfirmSave"
      />

      <AdsAssemblyVideoScriptsReviewModal
        v-if="isReviewModalOpen"
        v-model="isReviewModalOpen"
        :variants="variants"
        :states="variantStates"
        @review="handleReview"
        @saveChanges="handleSave"
      />

      <AdsAssemblyVideoDiversityMatrixModal
        v-if="isDiversityMatrixModalOpen"
        v-model="isDiversityMatrixModalOpen"
        :variants="variants"
      />

      <AdsAssemblyVideoScriptsContentReadyModal
        v-if="isContentReadyModalOpen"
        v-model="isContentReadyModalOpen"
        :initialOptions="store.currentAd?.draft.settings"
        :variants="variants"
        :productionMode="
          store.currentAd?.draft.settings?.production_mode ?? 'SCRIPTS_ONLY'
        "
        :model="store.currentAd?.draft.settings?.model ?? null"
        @confirm="handleConfirmContentReady"
      />
    </template>
  </FormStepLayout>
</template>
