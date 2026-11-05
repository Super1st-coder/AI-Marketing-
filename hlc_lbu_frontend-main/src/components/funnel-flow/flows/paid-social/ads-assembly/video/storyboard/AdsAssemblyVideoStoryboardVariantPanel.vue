<script setup lang="ts">
import {
  GenerateVideoStoryboardResponse,
  VideoScriptVariant,
} from "@/services/funnel-flow/paid-social/VideoApi";
import {
  StoryboardShotImage,
  StoryboardVariantShotImages,
  getActiveShotImage,
  getFailedShotIndexes,
} from "./storyboardShotImages";

const props = defineProps<{
  variant: VideoScriptVariant;
  shotImages: StoryboardVariantShotImages;
  isGeneratingVideo?: boolean;
  /** The most "Generate Video" can charge (every variant); shown on the button when known. */
  videoCost?: number;
  errorMessage?: string;
  /** Whether a failed shot is being retried, in this variant or another. */
  isRetryingShot?: boolean;
  /** `index` of this variant's shot being retried. */
  retryingShotIndex?: number;
  /** Why retrying one of this variant's shots failed. */
  retryShotError?: { shotIndex: number; message: string };
}>();

const emit = defineEmits<{
  generateVideo: [];
  /** Generates the frame of a failed shot again. */
  retryShot: [shotIndex: number];
  selectImage: [shotIndex: number, imageIndex: number];
  addImage: [shotIndex: number, image: StoryboardShotImage];
  /** The variant's frames, regenerated under a visual direction. */
  directionApplied: [storyboard: GenerateVideoStoryboardResponse];
}>();

const store = useFunnelPaidSocialAdsAssemblyStore();
const { locale } = useI18n();

function handleGoBack() {
  store.setPreviousVideoScreen("videoStoryboard");
}

const failedShotIndexes = computed(() =>
  getFailedShotIndexes(props.variant, props.shotImages),
);

// Scripts Only goes to the voiceover step next when it was enabled in the
// "Is the content ready?" modal
const isVoiceoverNext = computed(() => {
  const screens = store.currentVideoScreens;
  return screens[screens.indexOf("videoStoryboard") + 1] === "videoVoiceover";
});

const isVisualDirectionModalOpen = ref(false);

const isShotModalOpen = ref(false);
/** `index` of the shot the modal opens on. */
const shotModalInitialIndex = ref<number>();

function handleEditImage(shotIndex: number) {
  shotModalInitialIndex.value = shotIndex;
  isShotModalOpen.value = true;
}
</script>

<template>
  <div class="tw:flex tw:grow tw:flex-col">
    <Container class="tw:grow tw:pb-12" :maxWidth="910">
      <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-6" borderRadius="md">
        <div
          class="tw:flex tw:flex-col-reverse tw:gap-3 tw:sm:flex-row tw:sm:items-start tw:sm:justify-between"
        >
          <div>
            <h3 class="tw:mb-2 tw:text-xl tw:font-bold">
              {{ variant.title }}
            </h3>

            <p class="tw:text-sm tw:text-secondary-text">
              {{ variant.strategic_angle }}
            </p>
          </div>

          <Button
            class="tw:shrink-0 tw:self-start"
            variant="label"
            size="sm"
            leftIcon="custom:hi-luca"
            type="button"
            @click="isVisualDirectionModalOpen = true"
          >
            {{
              $t(
                "funnel-flow.paid-social.ads.video.storyboard.visual-direction",
              )
            }}
          </Button>
        </div>

        <!-- The shots are collapsed, so the failures are summed up here -->
        <Alert v-if="failedShotIndexes.length" type="error">
          {{
            $t(
              "funnel-flow.paid-social.ads.video.storyboard.errors.shots-failed",
              { count: failedShotIndexes.length },
            )
          }}

          <template #custom>
            <ul class="tw:mt-1 tw:list-disc tw:pl-5">
              <li v-for="shotIndex in failedShotIndexes" :key="shotIndex">
                {{
                  $t("funnel-flow.paid-social.ads.video.scripts.shot.title", {
                    number: shotIndex,
                  })
                }}
              </li>
            </ul>
          </template>
        </Alert>

        <AccordionList>
          <AdsAssemblyVideoStoryboardShot
            v-for="shot in variant.shots"
            :key="shot.index"
            :shot="shot"
            :image="getActiveShotImage(shotImages[shot.index])"
            :failed="failedShotIndexes.includes(shot.index)"
            :isRetrying="retryingShotIndex === shot.index"
            :retryDisabled="isRetryingShot || isGeneratingVideo"
            :retryErrorMessage="
              retryShotError?.shotIndex === shot.index
                ? retryShotError.message
                : undefined
            "
            @editImage="handleEditImage(shot.index)"
            @retry="emit('retryShot', shot.index)"
          />
        </AccordionList>
      </CardBase>

      <Alert v-if="errorMessage" type="error" autoScroll class="tw:mt-6">
        {{ errorMessage }}
      </Alert>
    </Container>

    <AdsAssemblyVideoScriptsVariantPanelFooter>
      <template #before>
        <ButtonGoBack
          :disabled="isGeneratingVideo || isRetryingShot"
          @click="handleGoBack"
        />
      </template>

      <!-- Waits for a retried shot, so the video starts from its new frame -->
      <Button
        :isLoading="isGeneratingVideo"
        :disabled="isRetryingShot"
        data-testid="video-storyboard-generate-video"
        @click="emit('generateVideo')"
      >
        {{
          isVoiceoverNext
            ? $t(
                "funnel-flow.paid-social.ads.video.storyboard.footer.generate-voiceover",
              )
            : videoCost === undefined
              ? $t(
                  "funnel-flow.paid-social.ads.video.storyboard.footer.generate-video",
                )
              : $t(
                  "funnel-flow.paid-social.ads.video.storyboard.footer.generate-video-cost",
                  { cost: formatNumberValue(videoCost, locale) },
                )
        }}
      </Button>
    </AdsAssemblyVideoScriptsVariantPanelFooter>

    <AdsAssemblyVideoStoryboardVisualDirectionModal
      v-if="isVisualDirectionModalOpen"
      v-model="isVisualDirectionModalOpen"
      :variant="variant"
      @applied="(storyboard) => emit('directionApplied', storyboard)"
    />

    <AdsAssemblyVideoStoryboardShotModal
      v-if="isShotModalOpen && shotModalInitialIndex !== undefined"
      v-model="isShotModalOpen"
      :variant="variant"
      :shotImages="shotImages"
      :initialShotIndex="shotModalInitialIndex"
      @selectImage="
        (shotIndex, imageIndex) => emit('selectImage', shotIndex, imageIndex)
      "
      @addImage="(shotIndex, image) => emit('addImage', shotIndex, image)"
    />
  </div>
</template>
