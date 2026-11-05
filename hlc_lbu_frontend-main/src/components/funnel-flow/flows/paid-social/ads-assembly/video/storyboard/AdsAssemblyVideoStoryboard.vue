<script setup lang="ts">
import VideoApi, {
  GenerateVideoSegmentsResponse,
  GenerateVideoStoryboardResponse,
  VideoDraft,
  VideoJobProgress,
  VideoScriptVariant,
  VideoSegment,
} from "@/services/funnel-flow/paid-social/VideoApi";
import {
  GenerationTakingTooLongError,
  getJobShotCounts,
  isGenerationOutcomeUnknown,
  watchVideoGenerationJob,
} from "../videoGenerationJob";
import {
  StoryboardShotImage,
  StoryboardShotImagesByVariant,
  createStoryboardShotImages,
  getActiveShotImage,
  getFailedShotIndexes,
  getVariantAnchorUrl,
} from "./storyboardShotImages";
import { saveVideoClipKeys } from "../../refine/editor/segments/segmentFiles";

const store = useFunnelPaidSocialAdsAssemblyStore();
const { t } = useI18n();
const { refresh: refreshCredits } = useVideoCredits();
const notificationStore = useNotificationStore();

const variants = computed(() =>
  Object.values(store.currentAd?.draft.variants ?? {}),
);

// The most "Generate Video" can charge: every variant's video, priced as /segments charges it
// (same model and saved resolution as the window that picks the variants). Shown on the button,
// like Continue in Settings (Marco, 2026-11-03). Only Full Video generates video. `undefined`
// while loading or unpriced: the window still shows "—" and blocks, so nothing is charged blind
const videoCost = ref<number>();
// Only the latest request sets the price: an older one can answer after a newer one
let videoPriceRequest = 0;

async function loadVideoCost() {
  const request = ++videoPriceRequest;
  videoCost.value = undefined;
  const settings = store.currentAd?.draft.settings;
  if (settings?.production_mode !== "FULL_VIDEO" || !variants.value.length) {
    return;
  }

  try {
    const estimate = await VideoApi.estimateVariants(
      variants.value,
      "FULL_VIDEO",
      settings.model ?? null,
      null,
      null,
      store.currentAd?.ad_id ?? null,
      settings.resolution ?? null,
    );
    if (request === videoPriceRequest && estimate.video.priced) {
      videoCost.value = estimate.video.lucas;
    }
  } catch (error) {
    console.error("Failed to estimate the video cost:", error);
  }
}

watch(
  () => [
    store.currentAd?.ad_id,
    store.currentAd?.draft.settings?.production_mode,
    store.currentAd?.draft.settings?.model,
    store.currentAd?.draft.settings?.resolution,
    variants.value.map((variant) => variant.shots.length).join(),
  ],
  loadVideoCost,
  { immediate: true },
);

// The frames saved in the draft by the Scripts step. Shots without a frame
// (failed, or the storyboard wasn't generated) show the placeholder
// TODO: save the edited versions, they're lost when leaving the step
const shotImages = ref<StoryboardShotImagesByVariant>(
  createStoryboardShotImages(variants.value),
);

// Picking a version from the history doesn't consume credits
async function handleSelectImage(
  variantId: string,
  shotIndex: number,
  imageIndex: number,
) {
  const images = shotImages.value[variantId]?.[shotIndex];
  if (!images || !images.history[imageIndex] || !store.currentAd) return;

  images.activeIndex = imageIndex;

  // The draft keeps one frame per shot and a save replaces the whole list, so
  // the pick is saved by sending the frame each shot is using. Frames without
  // a storage key were never saved, so they aren't part of the list
  const frames = Object.entries(shotImages.value[variantId]).flatMap(
    ([index, shot]) => {
      const image = getActiveShotImage(shot);

      return image?.storage_key
        ? [
            {
              shot_index: Number(index),
              image_url: image.image_url,
              storage_key: image.storage_key,
            },
          ]
        : [];
    },
  );

  try {
    await VideoApi.saveDraft({
      ad_id: store.currentAd.ad_id,
      variants: { [variantId]: { frames } },
    });
    await store.refetchCurrentAd();
  } catch (error) {
    console.error("Failed to save the selected frame:", error);
  }
}

// A new version is added to the history and used right away
function handleAddImage(
  variantId: string,
  shotIndex: number,
  image: StoryboardShotImage,
) {
  const variantImages = (shotImages.value[variantId] ??= {});
  const images = (variantImages[shotIndex] ??= {
    history: [],
    activeIndex: 0,
  });

  images.history.push(image);
  images.activeIndex = images.history.length - 1;
}

// Each regenerated frame is a new version of its shot, so the previous ones
// can still be picked. Shots whose frame failed keep the one they had
function handleDirectionApplied(
  variantId: string,
  newStoryboard: GenerateVideoStoryboardResponse,
) {
  const variant = variants.value.find((item) => item.variant_id === variantId);
  if (!variant) return;

  for (const frame of newStoryboard.frames[variantId] ?? []) {
    const shot = variant.shots.find((item) => item.index === frame.shot_index);
    if (!shot) continue;

    handleAddImage(variantId, frame.shot_index, {
      image_url: frame.image_url,
      scene: shot.scene,
      storage_key: frame.storage_key,
    });
  }
}

// The shot whose failed frame is being generated again. One at a time: the
// backend saves each frame to the same draft, and two saving at once could
// overwrite each other
const retryingShot = ref<{ variantId: string; shotIndex: number }>();
const retryShotError = ref<{
  variantId: string;
  shotIndex: number;
  message: string;
}>();

// A failed frame is generated on its own, so the frames that worked aren't
// generated (and billed) again with the whole storyboard. Billed as one image
async function handleRetryShot(variantId: string, shotIndex: number) {
  // Read once, in case the user opens another ad while it generates
  const ad = store.currentAd;
  const adSet = store.currentSet;
  const variant = variants.value.find((item) => item.variant_id === variantId);
  const shot = variant?.shots.find((item) => item.index === shotIndex);
  if (!ad || !adSet || !variant || !shot || retryingShot.value) return;

  retryingShot.value = { variantId, shotIndex };
  retryShotError.value = undefined;

  try {
    const response = await VideoApi.editStoryboardShot({
      id_adset: adSet.id,
      ad_index: store.currentAdIndex,
      id_ad: ad.ad_id,
      brand_id: String(store.brandId),
      variant,
      shot_index: shotIndex,
      // The backend needs a scene or feedback to generate anything. The
      // shot's own scene generates it as the storyboard planned it
      scene_override: shot.scene,
      feedback: "",
      // The shot has no frame to start from, so the protagonist is copied
      // from the variant's anchor frame instead
      use_current_as_reference: false,
      current_image_url: null,
      base_image_url: (await getVariantAnchorUrl(variant)) ?? null,
    });

    handleAddImage(variantId, shotIndex, {
      image_url: response.image_url,
      scene: response.scene,
      storage_key: response.storage_key,
    });
    void refreshCredits();

    // Load the draft the backend saved the new frame to.
    await store.refetchSingleAd(ad.ad_id);

    // The user can be on another variant's tab by now. When it was the
    // variant's last failed shot, it's said too: its tab gets the check and
    // the video can be generated
    const isVariantComplete = !getFailedShotIndexes(
      variant,
      shotImages.value[variantId],
    ).length;

    notificationStore.display({
      type: "success",
      title: t(
        "funnel-flow.paid-social.ads.video.storyboard.toasts.image-retried",
        { number: shotIndex },
      ),
      description: isVariantComplete
        ? t(
            "funnel-flow.paid-social.ads.video.storyboard.toasts.variant-complete",
            // By id: the draft was reloaded, so the variants are new objects
            {
              number:
                variants.value.findIndex(
                  (item) => item.variant_id === variantId,
                ) + 1,
            },
          )
        : undefined,
    });
  } catch (error) {
    console.error("Failed to retry the shot image:", error);
    // Out of credits, billing down... get their own message
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    retryShotError.value = {
      variantId,
      shotIndex,
      message: t(
        billingKey ??
          "funnel-flow.paid-social.ads.video.storyboard.shot.retry-failed",
      ),
    };
  } finally {
    retryingShot.value = undefined;
  }
}

const initialTab = variants.value[0]?.variant_id;
const currentTab = ref<string | undefined>(initialTab);

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
        stage: "storyboard",
      })
    ).pending
  : [];

// The flags saved in the backend. A variant can have one from before a shot
// failed, so they're only shown through `reviewedVariants`
const reviewedFlags = ref<Record<string, boolean>>(
  Object.fromEntries(
    variants.value.map((variant) => {
      const rowId = store.getVideoVariantRowId(variant.variant_id);

      return [
        variant.variant_id,
        rowId !== undefined && !pendingRowIds.includes(rowId),
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
      stage: "storyboard",
    });

    if (!response.saved) {
      console.error("The reviewed flag wasn't saved:", response);
    }
  } catch (error) {
    console.error("Failed to save the reviewed flag:", error);
  }
}

// A variant with a failed shot isn't reviewed, or the video could be
// generated with a shot missing its frame
const variantsWithFailedShots = computed(
  () =>
    new Set(
      variants.value
        .filter(
          (variant) =>
            getFailedShotIndexes(variant, shotImages.value[variant.variant_id])
              .length,
        )
        .map((variant) => variant.variant_id),
    ),
);

const reviewedVariants = computed<Record<string, boolean>>(() =>
  Object.fromEntries(
    variants.value.map((variant) => [
      variant.variant_id,
      Boolean(reviewedFlags.value[variant.variant_id]) &&
        !variantsWithFailedShots.value.has(variant.variant_id),
    ]),
  ),
);

// A variant counts as reviewed once its tab is open with every frame there.
// One with failed shots does once they're retried while it's open
watch(
  () =>
    currentTab.value && !variantsWithFailedShots.value.has(currentTab.value)
      ? currentTab.value
      : undefined,
  (variantId) => {
    // Saved only the first time, the backend already has it after that
    if (!variantId || reviewedFlags.value[variantId]) return;

    reviewedFlags.value[variantId] = true;
    void saveReviewedFlag(variantId);
  },
  { immediate: true },
);

watch(currentTab, () => {
  generalErrorMessage.value = undefined;
});

const hasPendingVariants = computed(() =>
  variants.value.some((variant) => !reviewedVariants.value[variant.variant_id]),
);

const isReviewModalOpen = ref(false);
const isGenerateModalOpen = ref(false);
const isDiversityMatrixModalOpen = ref(false);
const isGeneratingVideo = ref(false);
// Shows the loading screen instead of the storyboard while the clips generate
// and the videos are assembled. Full Video only: Scripts Only generates
// nothing here. On an error the storyboard comes back with the error
const isShowingVideoLoading = ref(false);

// The job of the clips being generated, for its progress
const segmentsJob = shallowRef<ReturnType<typeof watchVideoGenerationJob>>();
// The job as the request answered it. The last poll can be from before the
// last clip, and the loading screen stays while the videos are assembled
const finishedSegmentsJob = shallowRef<VideoJobProgress>();
// One clip per shot. Shown as "0 of N" until the job is found, so the
// progress doesn't pop in a few seconds later
const segmentsTotalShots = ref(0);
const segmentsShots = computed(() => {
  const job = finishedSegmentsJob.value ?? segmentsJob.value?.progress.value;
  return job
    ? getJobShotCounts(job)
    : { total: segmentsTotalShots.value, ready: 0, failed: 0 };
});
// The video being assembled once the clips are done, one per variant
const assemblingVideo = ref<{ number: number; total: number }>();
// The clips take the first half and assembling the second, an estimate:
// assembling has no progress of its own, so each finished video counts.
// Failed clips count as done, so the clips get to their 50%
const videoPercentage = computed(() => {
  const { total, ready, failed } = segmentsShots.value;
  const clipsDone = total ? (ready + failed) / total : 0;
  const videosDone = assemblingVideo.value
    ? (assemblingVideo.value.number - 1) / assemblingVideo.value.total
    : 0;

  return Math.round(clipsDone * 50 + videosDone * 50);
});

function getClipKey(clip: VideoSegment) {
  return clip.storage_key ?? clip.video_url;
}

// Every clip saved in the draft, to tell the new ones from them
function getClipKeys(draft: VideoDraft) {
  return new Set(
    Object.values(draft.variants).flatMap((variant) =>
      (variant.clips ?? []).map(getClipKey),
    ),
  );
}

// The clips the generation saved to the draft, by variant, in the same shape
// the request answers them
function getNewClips(draft: VideoDraft, previousClipKeys: Set<string>) {
  return Object.fromEntries(
    Object.entries(draft.variants).map(([variantId, variant]) => [
      variantId,
      (variant.clips ?? []).filter(
        (clip) => !previousClipKeys.has(getClipKey(clip)),
      ),
    ]),
  );
}

function handleReview(variantId: string) {
  currentTab.value = variantId;
}

function handleGenerateVideo() {
  if (hasPendingVariants.value) {
    isReviewModalOpen.value = true;
  } else if (
    store.currentAd?.draft.settings?.production_mode === "SCRIPTS_ONLY"
  ) {
    // Scripts Only doesn't generate video, so there's nothing to pick or
    // spend credits on: every variant moves on
    handleConfirmGenerate(variants.value.map((variant) => variant.variant_id));
  } else {
    isGenerateModalOpen.value = true;
  }
}

// The frame each shot uses, so the video starts from the version picked in
// the history. Shots without one are left out. The saved links expire within
// the hour and the video provider needs to download them, so the frames that
// have a storage key get a fresh link
async function getActiveFrames(selectedVariants: VideoScriptVariant[]) {
  const frames: Record<string, Record<number, string>> = {};

  await Promise.all(
    selectedVariants.flatMap((variant) => {
      frames[variant.variant_id] = {};

      return variant.shots.map(async (shot) => {
        const image = getActiveShotImage(
          shotImages.value[variant.variant_id]?.[shot.index],
        );

        if (!image) return;

        frames[variant.variant_id][shot.index] = image.storage_key
          ? (await VideoApi.getDownloadUrl(image.storage_key)).url
          : image.image_url;
      });
    }),
  );

  return frames;
}

async function handleConfirmGenerate(variantIds: string[]) {
  // Read once: generating takes minutes, and the user can open another ad in
  // the meantime, so `store.currentAd` may no longer be this one when it ends
  const ad = store.currentAd;
  const adSet = store.currentSet;
  if (!ad || !adSet) return;

  isGeneratingVideo.value = true;
  generalErrorMessage.value = undefined;

  try {
    // Scripts Only doesn't generate the video, the clips are uploaded instead
    if (ad.draft.settings.production_mode === "FULL_VIDEO") {
      const selectedVariants = variants.value.filter((variant) =>
        variantIds.includes(variant.variant_id),
      );
      const adIndex = store.currentAdIndex;
      const previousClipKeys = getClipKeys(ad.draft);

      segmentsTotalShots.value = selectedVariants.reduce(
        (total, variant) => total + variant.shots.length,
        0,
      );
      isShowingVideoLoading.value = true;

      const job = watchVideoGenerationJob({
        adId: ad.ad_id,
        step: "segments",
        previousJobId: ad.draft.jobs?.segments,
      });
      segmentsJob.value = job;

      let response: GenerateVideoSegmentsResponse | undefined;

      try {
        response = await VideoApi.generateSegments({
          id_adset: adSet.id,
          ad_index: adIndex,
          id_ad: ad.ad_id,
          brand_id: String(store.brandId),
          variants: selectedVariants,
          model: ad.draft.settings.model ?? null,
          // The same resolution the price window sent, so the charge is what it showed
          resolution: ad.draft.settings.resolution ?? null,
          storyboard_frames: await getActiveFrames(selectedVariants),
          visual_directions: Object.fromEntries(
            selectedVariants.flatMap((variant) =>
              variant.visual_direction
                ? [[variant.variant_id, variant.visual_direction]]
                : [],
            ),
          ),
        });
        finishedSegmentsJob.value = response.progress;
      } catch (error) {
        if (!isGenerationOutcomeUnknown(error)) throw error;

        // The backend keeps generating and saves the clips to the draft by
        // itself, so it goes on once they're there, as if it had answered
        await job.waitForResult((draft) =>
          Object.values(getNewClips(draft, previousClipKeys)).some(
            (clips) => clips.length,
          ),
        );
      } finally {
        job.stop();
      }

      // The clips are charged in Luca Credits. Assembling is free
      void refreshCredits();

      // Load the draft the backend saved the clips to
      const savedAd = await store.refetchSingleAd(ad.ad_id);
      // Without an answer, the clips are the new ones in the draft
      const segments =
        response?.segments ?? getNewClips(savedAd.draft, previousClipKeys);

      // Each shot's clip, in shot order. Undefined if a shot has none: its
      // clip failed, and the backend only assembles a video with every shot.
      // The Segments editor can regenerate the clip and assemble it later
      function getOrderedClips(variant: VideoScriptVariant) {
        const clips = variant.shots.map((shot) =>
          segments[variant.variant_id]?.find(
            (clip) => clip.shot_index === shot.index,
          ),
        );

        return clips.every((clip) => clip !== undefined) ? clips : undefined;
      }

      // One video per variant. They go one at a time, since each one saves to
      // the same draft and two saving at once would overwrite each other
      const variantsToAssemble = selectedVariants.flatMap((variant) => {
        const clips = getOrderedClips(variant);
        return clips ? [{ variant, clips }] : [];
      });

      for (const [index, { variant, clips }] of variantsToAssemble.entries()) {
        assemblingVideo.value = {
          number: index + 1,
          total: variantsToAssemble.length,
        };

        // A new assembly has a new link, even if it's stored with the same key
        const previousVideoUrl =
          savedAd.draft.variants[variant.variant_id]?.video?.video_url;
        // Assembling has no job, so only the draft tells when it's done
        const assembly = watchVideoGenerationJob({ adId: ad.ad_id });

        try {
          await VideoApi.assembleVideo({
            id_adset: adSet.id,
            ad_index: adIndex,
            id_ad: ad.ad_id,
            variant,
            clip_urls: clips.map((clip) => clip.video_url),
            // The audio is already in the clips in Full Video
            audio_urls: [],
            music_url: null,
            burn_subtitles: false,
            // So the backend marks the variant as having its video, which
            // publishing needs. Read from this ad's draft, since the user
            // may be on another ad by now
            variant_row_id: savedAd.draft.variant_rows[variant.variant_id],
          });
        } catch (error) {
          if (!isGenerationOutcomeUnknown(error)) throw error;

          await assembly.waitForResult((draft) => {
            const videoUrl =
              draft.variants[variant.variant_id]?.video?.video_url;
            return Boolean(videoUrl) && videoUrl !== previousVideoUrl;
          });
        } finally {
          assembly.stop();
        }

        // So the Segments editor knows the video is up to date until its
        // clips change. Before the next variant, which saves to the same draft
        await saveVideoClipKeys(ad.ad_id, variant.variant_id, clips);
      }

      // Load the draft the backend saved the videos to, shown in the Ad step
      await store.refetchSingleAd(ad.ad_id);
    } else {
      // The backend only saves the step when it generates something, so it
      // is saved here for the step that comes next
      await VideoApi.saveDraft({
        ad_id: ad.ad_id,
        current_step: ad.draft.settings.voiceover_enabled
          ? "voiceover"
          : "video",
      });
      await store.refetchSingleAd(ad.ad_id);
    }

    // Only moves on if the user is still on this ad. Scripts Only can go to
    // the voiceover step next
    if (store.currentAd?.ad_id === ad.ad_id) {
      store.setNextVideoScreen("videoStoryboard");
    }
  } catch (error) {
    console.error("Failed to generate video:", error);
    // Out of credits, video limit, billing down... get their own message
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    generalErrorMessage.value = t(
      billingKey ??
        (error instanceof GenerationTakingTooLongError
          ? "funnel-flow.paid-social.ads.video.generating.errors.taking-too-long"
          : "funnel-flow.paid-social.ads.video.storyboard.errors.video-generation-failed"),
    );
  } finally {
    isGeneratingVideo.value = false;
    isShowingVideoLoading.value = false;
    segmentsJob.value = undefined;
    finishedSegmentsJob.value = undefined;
    assemblingVideo.value = undefined;
  }
}
</script>

<template>
  <!-- No stepper while generating -->
  <AdsAssemblyVideoGenerating
    v-if="isShowingVideoLoading"
    :percentage="videoPercentage"
  >
    <template #title>
      {{ $t("funnel-flow.paid-social.ads.video.generating.video.title") }}
    </template>

    <template #subtitle>
      {{
        $t("funnel-flow.paid-social.ads.video.generating.video.subtitle", {
          campaign: store.campaign.name,
        })
      }}
    </template>

    <template #progress>
      <template v-if="assemblingVideo">
        {{
          $t(
            "funnel-flow.paid-social.ads.video.generating.video.assembling",
            assemblingVideo,
          )
        }}
      </template>

      <template v-else>
        {{
          $t(
            segmentsShots.failed
              ? "funnel-flow.paid-social.ads.video.generating.video.progress-with-failures"
              : "funnel-flow.paid-social.ads.video.generating.video.progress",
            segmentsShots,
          )
        }}
      </template>
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
            {{ $t("funnel-flow.paid-social.ads.video.storyboard.title") }}

            <template #description>
              {{
                $t("funnel-flow.paid-social.ads.video.storyboard.description")
              }}
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
                  reviewedVariants[variant.variant_id]
                    ? 'tabler:circle-check'
                    : undefined
                "
                iconClass="tw:text-success"
                :hasAlert="!reviewedVariants[variant.variant_id]"
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
            <AdsAssemblyVideoStoryboardVariantPanel
              class="tw:mt-5"
              :variant="variant"
              :shotImages="shotImages[variant.variant_id] ?? {}"
              :isGeneratingVideo="isGeneratingVideo"
              :videoCost="videoCost"
              :errorMessage="generalErrorMessage"
              :isRetryingShot="Boolean(retryingShot)"
              :retryingShotIndex="
                retryingShot?.variantId === variant.variant_id
                  ? retryingShot.shotIndex
                  : undefined
              "
              :retryShotError="
                retryShotError?.variantId === variant.variant_id
                  ? retryShotError
                  : undefined
              "
              @generateVideo="handleGenerateVideo"
              @retryShot="
                (shotIndex) => handleRetryShot(variant.variant_id, shotIndex)
              "
              @selectImage="
                (shotIndex, imageIndex) =>
                  handleSelectImage(variant.variant_id, shotIndex, imageIndex)
              "
              @addImage="
                (shotIndex, image) =>
                  handleAddImage(variant.variant_id, shotIndex, image)
              "
              @directionApplied="
                (newStoryboard) =>
                  handleDirectionApplied(variant.variant_id, newStoryboard)
              "
            />
          </TabPanel>
        </Tabs>
      </div>

      <AdsAssemblyVideoStoryboardReviewModal
        v-if="isReviewModalOpen"
        v-model="isReviewModalOpen"
        :variants="variants"
        :reviewed="reviewedVariants"
        @review="handleReview"
      />

      <AdsAssemblyVideoStoryboardGenerateModal
        v-if="isGenerateModalOpen"
        v-model="isGenerateModalOpen"
        :variants="variants"
        :model="store.currentAd?.draft.settings?.model ?? null"
        @confirm="handleConfirmGenerate"
      />

      <AdsAssemblyVideoDiversityMatrixModal
        v-if="isDiversityMatrixModalOpen"
        v-model="isDiversityMatrixModalOpen"
        :variants="variants"
      />
    </template>
  </FormStepLayout>
</template>
