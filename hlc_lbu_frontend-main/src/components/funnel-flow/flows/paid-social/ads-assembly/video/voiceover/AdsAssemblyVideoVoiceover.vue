<script setup lang="ts">
import VideoApi, {
  GenerateVideoVoiceoverRequest,
  VIDEO_VOICE_LANGUAGES,
  VideoVoice,
  VideoVoiceLanguage,
} from "@/services/funnel-flow/paid-social/VideoApi";
import {
  VoiceoverVariantState,
  createVoiceoverVariantAudio,
  createVoiceoverVariantState,
  getListedVoices,
  getSavedVoiceIds,
} from "./voiceoverVariants";
import { appLocalesArray } from "@/plugins/i18n";

const store = useFunnelPaidSocialAdsAssemblyStore();
const { refresh: refreshCredits } = useVideoCredits();
const { t } = useI18n();

const variants = computed(() =>
  Object.values(store.currentAd?.draft.variants ?? {}),
);

// The Settings language when the catalogue supports it. Scripts generated
// before Settings sent one have it empty, so the campaign's language is used
// then, like Settings does. Otherwise Spanish, like the backend's default
const language = computed<VideoVoiceLanguage>(() => {
  const settingsLanguage =
    store.currentAd?.draft.settings.language ||
    appLocalesArray.find((locale) => locale.apiName === store.campaign.language)
      ?.code;

  return (
    VIDEO_VOICE_LANGUAGES.find((item) => item === settingsLanguage) ?? "es"
  );
});

// The accent is shared by every variant. It starts as the one picked in
// Settings, and leaving it out loads the language's default one
const catalogue = ref(
  await VideoApi.getVoices({
    language: language.value,
    accent: store.currentAd?.draft.settings.voice_accent || undefined,
  }),
);
const isLoadingVoices = ref(false);
const voicesErrorMessage = ref<string>();

// The draft only keeps the id of the voice the audio was generated with. The
// ones the suggestions don't have are looked up, so their name can be shown.
// One that can't be found shows its id instead
const savedVoices = (
  await Promise.all(
    getSavedVoiceIds(variants.value)
      .filter(
        (voiceId) =>
          !catalogue.value.suggested.some(
            (voice) => voice.voice_id === voiceId,
          ),
      )
      .map(async (voiceId): Promise<VideoVoice | undefined> => {
        try {
          const { found, voice_id, name, accent, preview_url } =
            await VideoApi.getVoice(voiceId);

          return found ? { voice_id, name, accent, preview_url } : undefined;
        } catch (error) {
          console.error("Failed to load the voice:", error);
          return undefined;
        }
      }),
  )
).filter((voice) => voice !== undefined);

const variantStates = ref<Record<string, VoiceoverVariantState>>(
  Object.fromEntries(
    variants.value.map((variant) => [
      variant.variant_id,
      createVoiceoverVariantState(
        variant,
        catalogue.value.suggested,
        savedVoices,
      ),
    ]),
  ),
);

async function handleChangeAccent(accent: string) {
  isLoadingVoices.value = true;
  voicesErrorMessage.value = undefined;

  try {
    catalogue.value = await VideoApi.getVoices({
      language: language.value,
      accent,
    });

    // A selected voice has to be in the list, so the ones the new accent
    // doesn't suggest are deselected. Voices added from the search stay
    for (const state of Object.values(variantStates.value)) {
      const voiceId = state.selectedVoice?.voice_id;
      const isListed = getListedVoices(
        state.addedVoices,
        catalogue.value.suggested,
      ).some((voice) => voice.voice_id === voiceId);

      if (!isListed) {
        state.selectedVoice = null;
      }
    }
  } catch (error) {
    console.error("Failed to load the voices:", error);
    voicesErrorMessage.value = t(
      "funnel-flow.paid-social.ads.video.voiceover.errors.voices-loading-failed",
    );
  } finally {
    isLoadingVoices.value = false;
  }
}

const initialTab = variants.value[0]?.variant_id;
const currentTab = ref<string | undefined>(initialTab);

const captionsErrorMessage = ref<string>();

watch(
  currentTab,
  (variantId) => {
    if (!variantId) return;

    variantStates.value[variantId].visited = true;
    captionsErrorMessage.value = undefined;
  },
  { immediate: true },
);

function hasFailedShots(variantId: string) {
  return Boolean(
    variantStates.value[variantId]?.audio?.failedShotIndexes.length,
  );
}

// A variant counts as reviewed once its audio is generated for every shot.
// One with a failed shot isn't, or the captions could be generated with a
// shot missing its audio
function isVariantReviewed(variantId: string) {
  return (
    Boolean(variantStates.value[variantId]?.audio?.clips.length) &&
    !hasFailedShots(variantId)
  );
}

const reviewedVariants = computed(() =>
  Object.fromEntries(
    variants.value.map((variant) => [
      variant.variant_id,
      isVariantReviewed(variant.variant_id),
    ]),
  ),
);

const hasPendingVariants = computed(() =>
  variants.value.some((variant) => !isVariantReviewed(variant.variant_id)),
);

const isGeneratingAnyAudio = computed(() =>
  Object.values(variantStates.value).some((state) => state.isGenerating),
);

// A variant with a failed shot shows the warning instead
function getTabIcon(variantId: string) {
  if (hasFailedShots(variantId)) return undefined;
  if (isVariantReviewed(variantId)) return "tabler:circle-check";
  if (variantStates.value[variantId]?.visited) return "tabler:microphone-off";

  return undefined;
}

// Saved for the backend's review gate. The tab shows it from the audio, which
// is restored from the draft, so it doesn't wait for it
async function saveReviewedFlag(rowId: number | undefined) {
  if (rowId === undefined) return;

  try {
    const response = await VideoApi.markVariantReviewed({
      variant_id: rowId,
      stage: "voiceover",
    });

    if (!response.saved) {
      console.error("The reviewed flag wasn't saved:", response);
    }
  } catch (error) {
    console.error("Failed to save the reviewed flag:", error);
  }
}

async function handleGenerateAudio(variantId: string) {
  const variant = variants.value.find((item) => item.variant_id === variantId);
  const state = variantStates.value[variantId];
  const voice = state?.selectedVoice;
  // Read before generating, since the user can open another ad meanwhile
  const rowId = store.getVideoVariantRowId(variantId);

  if (
    !store.currentAd ||
    !store.currentSet ||
    !variant ||
    !voice ||
    state.isGenerating
  ) {
    return;
  }

  state.isGenerating = true;
  state.errorMessage = undefined;

  try {
    const request: GenerateVideoVoiceoverRequest = {
      id_adset: store.currentSet.id,
      ad_index: store.currentAdIndex,
      id_ad: store.currentAd.ad_id,
      brand_id: String(store.brandId),
      variants: [variant],
      voice_ids: { [variantId]: voice.voice_id },
    };

    const response = await VideoApi.generateVoiceover(request);

    // The audio is charged in Luca Credits: keep the counter current
    void refreshCredits();

    // Keeps the voice, since the selection can change afterwards
    state.audio = createVoiceoverVariantAudio(variantId, voice, response);

    // Generating is the review in this step, but only when every shot got
    // its audio. Regenerating keeps it, the backend never clears it
    if (state.audio.clips.length && !state.audio.failedShotIndexes.length) {
      void saveReviewedFlag(rowId);
    }

    // Load the draft the backend saved the audio to
    await store.refetchCurrentAd();
  } catch (error) {
    console.error("Failed to generate the voiceover:", error);
    // Out of credits or billing down: the balance is read again
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    state.errorMessage = t(
      billingKey ??
        "funnel-flow.paid-social.ads.video.voiceover.errors.audio-generation-failed",
    );
  } finally {
    state.isGenerating = false;
  }
}

const isReviewModalOpen = ref(false);

// Whether the open variant can generate its audio from the review modal
const canGenerateCurrent = computed(() => {
  const state = currentTab.value
    ? variantStates.value[currentTab.value]
    : undefined;

  return Boolean(state?.selectedVoice) && !isLoadingVoices.value;
});

async function handleReview(variantId: string) {
  // Goes through the save lock like a tab click, so leaving a variant while
  // its audio is generating asks first
  if ((await useSaveLockingStore().execute()) === "cancel") return;

  currentTab.value = variantId;
}

const isGeneratingCaptions = ref(false);

function handleGenerateCaptions() {
  if (hasPendingVariants.value) {
    isReviewModalOpen.value = true;
    return;
  }

  generateCaptions();
}

async function generateCaptions() {
  // Read before generating, since the user can open another ad meanwhile
  const ad = store.currentAd;

  if (!ad) return;

  isGeneratingCaptions.value = true;
  captionsErrorMessage.value = undefined;

  try {
    // TODO: replace with the endpoint that generates the captions
    await sleep(SECOND_IN_MS * 2);

    // The backend only saves the step when it generates something, so it is
    // saved here for the step that comes next, or the ad reopens here
    await VideoApi.saveDraft({ ad_id: ad.ad_id, current_step: "video" });
    await store.refetchSingleAd(ad.ad_id);

    // Only moves on if the user is still on this ad
    if (store.currentAd?.ad_id === ad.ad_id) {
      store.setNextVideoScreen("videoVoiceover");
    }
  } catch (error) {
    console.error("Failed to generate captions:", error);
    captionsErrorMessage.value = t(
      "funnel-flow.paid-social.ads.video.voiceover.errors.captions-generation-failed",
    );
  } finally {
    isGeneratingCaptions.value = false;
  }
}
</script>

<template>
  <FormStepLayout as="div" maxWidth="auto">
    <template #stepper>
      <AdsAssemblyVideoStepper />
    </template>

    <template #custom>
      <div class="tw:flex tw:h-full tw:flex-col tw:gap-6 tw:pt-6">
        <Container :maxWidth="910">
          <!-- TODO: add help video URL later -->
          <PageTitle helpButton>
            {{ $t("funnel-flow.paid-social.ads.video.voiceover.title") }}

            <template #description>
              {{
                $t("funnel-flow.paid-social.ads.video.voiceover.description")
              }}
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
                :icon="getTabIcon(variant.variant_id)"
                :iconClass="
                  isVariantReviewed(variant.variant_id)
                    ? 'tw:text-success'
                    : 'tw:text-gray-500'
                "
                :hasAlert="
                  hasFailedShots(variant.variant_id) ||
                  (!variantStates[variant.variant_id].visited &&
                    !isVariantReviewed(variant.variant_id))
                "
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
            <AdsAssemblyVideoVoiceoverVariantPanel
              v-model:selectedVoice="
                variantStates[variant.variant_id].selectedVoice
              "
              v-model:addedVoices="
                variantStates[variant.variant_id].addedVoices
              "
              class="tw:mt-5"
              :variant="variant"
              :state="variantStates[variant.variant_id]"
              :catalogue="catalogue"
              :isLoadingVoices="isLoadingVoices"
              :voicesErrorMessage="voicesErrorMessage"
              :isGeneratingAnyAudio="isGeneratingAnyAudio"
              :isGeneratingCaptions="isGeneratingCaptions"
              :captionsErrorMessage="captionsErrorMessage"
              @changeAccent="handleChangeAccent"
              @generateAudio="handleGenerateAudio(variant.variant_id)"
              @generateCaptions="handleGenerateCaptions"
            />
          </TabPanel>
        </Tabs>
      </div>

      <AdsAssemblyVideoVoiceoverReviewModal
        v-if="isReviewModalOpen"
        v-model="isReviewModalOpen"
        :variants="variants"
        :reviewed="reviewedVariants"
        :currentVariantId="currentTab"
        :canGenerate="canGenerateCurrent"
        @review="handleReview"
        @generateAudio="handleGenerateAudio"
      />
    </template>
  </FormStepLayout>
</template>
