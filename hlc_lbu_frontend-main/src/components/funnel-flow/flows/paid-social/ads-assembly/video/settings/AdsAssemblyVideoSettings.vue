<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, boolean, mixed, number, object, string } from "yup";
import { AdsAssemblyVideoSettingsEstimation } from "./AdsAssemblyVideoSettingsCreditEstimation.vue";
import VideoApi, {
  VIDEO_VOICE_LANGUAGES,
  VideoCostEstimate,
  VideoProductionMode,
  VideoSettings,
  VideoType,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { getVideoVoiceAccentLabel } from "../videoVoiceAccent";
import { SelectOption } from "@/components/forms/base/select-option.ts";
import { InsufficientCreditsError } from "@/services/common-errors";
import { appLocalesArray } from "@/plugins/i18n";

const PRODUCTION_MODES: VideoProductionMode[] = ["SCRIPTS_ONLY", "FULL_VIDEO"];

// Only Classic UGC AI is available for now; the rest are shown as "soon"
const VIDEO_TYPES: VideoType[] = ["CLASSIC_UGC_AI"];

// Values are what the backend expects
const FORMATS: { value: string; label: string }[] = [
  { value: "MP4", label: "MP4" },
  { value: "MOV", label: "MOV" },
];

const MIN_VIDEO_DURATION_SECONDS = 8;
const MAX_VIDEO_DURATION_SECONDS = 2 * 60;

const store = useFunnelPaidSocialAdsAssemblyStore();
const { t, te, locale } = useI18n();

// The campaign's language ("English", "Spanish") as the code the backend
// expects. Empty follows the ad set context
const language =
  appLocalesArray.find((locale) => locale.apiName === store.campaign.language)
    ?.code ?? "";

const [modelCatalogue, voiceCatalogue] = await Promise.all([
  VideoApi.getModels(),
  // The accents of the language, as the provider's codes. Spanish, like the
  // backend, when the language isn't one the voices support
  VideoApi.getVoices({
    language: VIDEO_VOICE_LANGUAGES.find((code) => code === language) ?? "es",
  }),
]);

const voiceAccentOptions = voiceCatalogue.accents.map((accent) => ({
  value: accent,
  label: getVideoVoiceAccentLabel(accent),
}));

const billableModels = modelCatalogue.models.filter((model) => model.billable);

// Models the backend can't price are listed but can't be selected
const modelOptions = modelCatalogue.models.map<SelectOption>((model) => ({
  value: model.model_id,
  label: model.ui_name,
  disabled: !model.billable,
}));

function getModel(id: string | undefined) {
  return modelCatalogue.models.find((model) => model.model_id === id);
}

// Resolutions are listed from lowest to highest, so prefer the highest
function getDefaultResolution(modelId: string | undefined) {
  return getModel(modelId)?.resolutions.at(-1);
}

// The backend's default could be a model it can't price, which can't be selected
const defaultModelId = getModel(modelCatalogue.default)?.billable
  ? modelCatalogue.default
  : billableModels[0]?.model_id;

function formatVideoDuration(seconds: number) {
  // return formatDurationDigital(locale.value, seconds);

  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}m`;
}

const schema = computed(() =>
  toTypedSchema(
    object({
      selectedVariations: number().required(t("forms.required-field")),
      generationMode: mixed<VideoProductionMode>()
        .oneOf(PRODUCTION_MODES)
        .required(t("forms.required-field")),
      videoType: mixed<VideoType>()
        .oneOf(VIDEO_TYPES)
        .required(t("forms.required-field")),
      model: string()
        .oneOf(billableModels.map((model) => model.model_id))
        .when("generationMode", {
          is: "FULL_VIDEO",
          then: (fieldSchema) =>
            fieldSchema.required(t("forms.required-field")),
        }),
      resolution: string()
        .when("model", ([modelId], fieldSchema) =>
          fieldSchema.oneOf(getModel(modelId)?.resolutions ?? []),
        )
        .when("generationMode", {
          is: "FULL_VIDEO",
          then: (fieldSchema) =>
            fieldSchema.required(t("forms.required-field")),
        }),
      format: string()
        .oneOf(FORMATS.map((option) => option.value))
        .when("generationMode", {
          is: "FULL_VIDEO",
          then: (fieldSchema) =>
            fieldSchema.required(t("forms.required-field")),
        }),
      music: boolean(),
      voiceAccent: string()
        .oneOf(voiceCatalogue.accents)
        .required(t("forms.required-field")),
      referenceImages: array().of(mixed<File>().required()),
      referenceVideo: array().of(mixed<File>().required()),
      referenceNotes: string(),
      videoDuration: number()
        .min(MIN_VIDEO_DURATION_SECONDS)
        .max(MAX_VIDEO_DURATION_SECONDS)
        .required(t("forms.required-field")),
    }),
  ),
);

// The settings the scripts were generated with, empty until then. A saved
// value the form can no longer offer (a model that isn't billable anymore, an
// option that was removed) falls back to the default, since the form would
// reject it
const savedSettings = store.currentAd?.draft.settings ?? {};

const initialModelId = getModel(savedSettings.model ?? undefined)?.billable
  ? (savedSettings.model ?? undefined)
  : defaultModelId;

const initialResolution =
  savedSettings.resolution &&
  getModel(initialModelId)?.resolutions.includes(savedSettings.resolution)
    ? savedSettings.resolution
    : getDefaultResolution(initialModelId);

const { handleSubmit, isSubmitting, values, setFieldValue, meta } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    keepValuesOnUnmount: true,
    initialValues: {
      selectedVariations: savedSettings.variants_per_ad ?? 1,
      generationMode: savedSettings.production_mode ?? "FULL_VIDEO",
      videoType:
        VIDEO_TYPES.find((type) => type === savedSettings.video_type) ??
        "CLASSIC_UGC_AI",
      model: initialModelId,
      resolution: initialResolution,
      format:
        FORMATS.find((option) => option.value === savedSettings.output_format)
          ?.value ?? "MP4",
      music: savedSettings.music ?? false,
      voiceAccent:
        voiceCatalogue.accents.find(
          (accent) => accent === savedSettings.voice_accent,
        ) ?? voiceCatalogue.default_accent,
      // The uploaded files aren't kept, only references to them
      referenceImages: [],
      referenceVideo: [],
      referenceNotes: savedSettings.external_references?.replicate_notes ?? "",
      videoDuration: savedSettings.target_duration_s ?? 30,
    },
  });

const { value: selectedVariations } = useField<number>("selectedVariations");
const { value: generationMode } =
  useField<VideoProductionMode>("generationMode");
const { value: videoType } = useField<VideoType>("videoType");

const referenceTab = ref<"image" | "video">("image");

const selectedModel = computed(() => getModel(values.model));

// The model only matters in Full Video, where it generates the video. Scripts Only doesn't
// use it, so it never limits the references there.
const isVideoReferenceHidden = computed(
  () =>
    generationMode.value === "FULL_VIDEO" &&
    selectedModel.value?.accepts_video_reference === false,
);

// A model that can't take a video reference must not keep one: leave the tab and drop the file
watch(isVideoReferenceHidden, (isHidden) => {
  if (!isHidden) return;

  referenceTab.value = "image";
  setFieldValue("referenceVideo", []);
});

// The model's limit in Full Video, same as above. Otherwise, or when the catalogue gives no
// limit for the model (`null`), the Figma's
const maxReferenceImages = computed(
  () =>
    (generationMode.value === "FULL_VIDEO"
      ? selectedModel.value?.max_reference_images
      : null) ?? ADS_ASSEMBLY_VIDEO_REFERENCE_IMAGES_MAX_COUNT,
);

// Says what the fields below take: the image limit, and the video only when its tab shows
const referencesDescription = computed(() => {
  const key = "funnel-flow.paid-social.ads.video.settings.external-references";
  const max = maxReferenceImages.value;
  const images = t(`${key}.description-images-up-to`, { count: max }, max);

  return isVideoReferenceHidden.value
    ? t(`${key}.description-without-video`, { images })
    : t(`${key}.description`, { images });
});

// A lower limit can't keep the images over it: keep the first ones
watch(maxReferenceImages, (max) => {
  const images = values.referenceImages ?? [];
  if (images.length > max)
    setFieldValue("referenceImages", images.slice(0, max));
});

const resolutionOptions = computed(
  () =>
    selectedModel.value?.resolutions.map((resolution) => ({
      value: resolution,
      label: resolution,
    })) ?? [],
);

// Each model supports different resolutions, so keep the current one only if
// the new model supports it
watch(
  () => values.model,
  (modelId) => {
    const resolutions = getModel(modelId)?.resolutions ?? [];

    if (!values.resolution || !resolutions.includes(values.resolution)) {
      setFieldValue("resolution", getDefaultResolution(modelId));
    }
  },
);

const generationModeOptions = computed(() =>
  PRODUCTION_MODES.map((mode) => ({
    value: mode,
    label: t(
      `funnel-flow.paid-social.ads.video.settings.generation-mode.${mode}`,
    ),
  })),
);

const { balance: creditsBalance, refresh: refreshCredits } = useVideoCredits();

/** The settings sent to Fury, from the form. Shared by the estimate and the generation. */
function buildVideoSettings(formValues: typeof values): VideoSettings | null {
  if (!store.currentSet) return null;
  // While the form is still incomplete there is nothing to price (or send) yet
  if (
    formValues.selectedVariations == null ||
    !formValues.generationMode ||
    !formValues.videoType ||
    formValues.videoDuration == null
  ) {
    return null;
  }

  const isFullVideo = formValues.generationMode === "FULL_VIDEO";

  return {
    ads_count: store.currentSet.ads.length,
    variants_per_ad: formValues.selectedVariations,
    production_mode: formValues.generationMode,
    video_type: formValues.videoType,
    model: isFullVideo ? (formValues.model ?? null) : null,
    resolution: isFullVideo ? (formValues.resolution ?? null) : null,
    output_format: formValues.format ?? "MP4",
    music: formValues.music ?? false,
    language,
    voice_accent: formValues.voiceAccent ?? voiceCatalogue.default_accent,
    target_duration_s: formValues.videoDuration,
    external_references: {
      // Uploaded on Continue, see `uploadReferences`
      images: [],
      video: null,
      replicate_notes: formValues.referenceNotes ?? "",
    },
    // Set later by the "Is the content ready?" modal of the Scripts step
    // (Scripts Only)
    storyboard_enabled: null,
    voiceover_enabled: null,
  };
}

// Real cost of the batch, priced by the credits service. Free (it holds and charges nothing),
// so it's recomputed as the user changes the options. A failed or pending estimate shows "—",
// never a stale or made-up number.
const costEstimate = ref<VideoCostEstimate | null>(null);
let latestEstimateRequest = 0;

/**
 * Set when Continue found the price had changed since it was shown: the button now shows the
 * new one, nothing was generated, and the user clicks again to accept it. Declared before the
 * settings watch below, which resets it and runs immediately on setup: declared after it, the
 * page crashed on open ("cannot access before initialization", QAS 2026-10-30).
 */
const priceChangedTo = ref<number>();

const refreshEstimate = useDebounceFn(async () => {
  const settings = buildVideoSettings(values);
  if (!settings) return;

  // storyboard_enabled is null here ("not decided yet"): the estimate prices it as the base
  // price in Scripts Only (the content-ready modal adds it later) and as included in Full
  // Video, where the storyboard always runs (backend #856).
  const request = ++latestEstimateRequest;
  try {
    const result = await VideoApi.estimateCost(settings, store.currentSet?.id);
    // Only the answer to the latest options counts
    if (request === latestEstimateRequest) costEstimate.value = result;
  } catch (error) {
    console.error("Failed to estimate the video cost:", error);
    if (request === latestEstimateRequest) costEstimate.value = null;
  }
}, 400);

watch(
  () => JSON.stringify(buildVideoSettings(values)),
  () => {
    costEstimate.value = null;
    priceChangedTo.value = undefined;
    void refreshEstimate();
  },
  { immediate: true },
);

/** Steps charged when the user presses Continue (the rest of the batch is charged later). */
const THIS_STEP_ACTIONS = ["video_scripts", "video_andromeda_score"];

/** Billable steps in display order; unknown ones follow, under their raw id. */
const ESTIMATE_ROW_ORDER = [
  "video_scripts",
  "video_andromeda_score",
  "video_storyboard",
  "video_voiceover",
  "video_segment",
];

const estimateRows = computed(() => {
  const estimate = costEstimate.value;
  if (!estimate) return [];

  // Scripts and scoring are priced in tokens (an input and an output line each); the user
  // thinks in scripts, so those rows count scripts. Frames and seconds are counted as-is.
  const scriptCount =
    (store.currentSet?.ads.length ?? 0) * (values.selectedVariations ?? 0);

  const groups = new Map<string, { quantity: number; subtotal: number }>();
  for (const line of estimate.lines) {
    const group = groups.get(line.action) ?? { quantity: 0, subtotal: 0 };
    group.subtotal += line.lucas;
    if (line.unit !== "per_1k_tokens") group.quantity += line.qty;
    groups.set(line.action, group);
  }

  return [...groups.entries()]
    .sort(
      ([a], [b]) =>
        (ESTIMATE_ROW_ORDER.indexOf(a) + 1 || 99) -
        (ESTIMATE_ROW_ORDER.indexOf(b) + 1 || 99),
    )
    .map(([action, group]) => {
      const quantity = THIS_STEP_ACTIONS.includes(action)
        ? scriptCount
        : group.quantity;
      const labelKey = `funnel-flow.paid-social.ads.video.credits.estimate.operations.${action}`;
      return {
        action,
        operation: te(labelKey) ? t(labelKey) : action,
        quantity,
        unitCost: quantity > 0 ? group.subtotal / quantity : 0,
        subtotal: group.subtotal,
      };
    });
});

/**
 * What pressing Continue charges: scripts + scoring for THIS ad only (generation runs one ad at
 * a time), while the estimate above prices every ad of the ad set.
 *
 * Rounded the way the ledger charges it: each line (scripts in/out, scoring in/out) is its own
 * charge, rounded up to a whole LUCA. Rounding the ad's total once came out ~1-2 LUCA under the
 * charge on every run (QAS, Zinus, 2026-10-14: button 72, charged 75).
 */
function stepCostOf(estimate: VideoCostEstimate | null) {
  const adsCount = store.currentSet?.ads.length ?? 0;
  if (!estimate || adsCount < 1) return undefined;

  return estimate.lines
    .filter((line) => THIS_STEP_ACTIONS.includes(line.action))
    .reduce((total, line) => total + Math.ceil(line.lucas / adsCount), 0);
}

const thisStepCost = computed(() => stepCostOf(costEstimate.value));

/**
 * The whole batch costs more than the company has. A notice, not a block: Continue only
 * charges this ad's scripts, and the backend refuses any later step that can't be paid.
 */
const overBalanceWarning = computed(() => {
  const total = costEstimate.value?.total_lucas;
  const available = creditsBalance.value?.available;
  if (total === undefined || available === undefined || total <= available) {
    return undefined;
  }
  // Can't even pay this step: don't suggest starting it, point to "Add credits" instead
  const key =
    missingCredits.value > 0
      ? "funnel-flow.paid-social.ads.video.credits.estimate.over-balance-blocked"
      : "funnel-flow.paid-social.ads.video.credits.estimate.over-balance";
  return t(key, {
    total: formatNumberValue(total, locale.value),
    available: formatNumberValue(available, locale.value),
    step: formatLucas(thisStepCost.value),
  });
});

/** Whole Lucas, rounded up: the screen never shows less than what may be charged. */
function formatLucas(value: number | undefined) {
  return value === undefined
    ? "—"
    : formatNumberValue(Math.ceil(value), locale.value);
}

const estimation = computed<AdsAssemblyVideoSettingsEstimation>(() => ({
  totalCost: costEstimate.value?.total_lucas,
  adsCount: store.currentSet?.ads.length,
  availableBalance: creditsBalance.value?.available,
  breakdown: estimateRows.value,
  note:
    costEstimate.value && !costEstimate.value.complete
      ? t("funnel-flow.paid-social.ads.video.credits.estimate.incomplete")
      : undefined,
  warning: overBalanceWarning.value,
}));

function handleGoBack() {
  store.setScreen("home");
}

const generalErrorMessage = ref<string>();

/**
 * Lucas this step needs beyond what the company has. While positive, Continue becomes "Add
 * credits" and nothing is generated (Marco, 2026-10-09). Unknown balance or cost never blocks:
 * the backend still refuses anything that can't be paid.
 */
const missingCredits = computed(() => {
  const available = creditsBalance.value?.available;
  const cost = thisStepCost.value;
  if (available === undefined || cost === undefined) return 0;
  return Math.max(0, Math.ceil(cost) - available);
});

const isAddCreditsOpen = ref(false);

// Uploads the reference files and returns their stored keys. On Continue
// rather than when picked, so files removed before continuing aren't kept
async function uploadReferences(formValues: typeof values) {
  const upload = async (file: File) =>
    (await VideoApi.uploadVideoAsset(file)).data.storage_key;

  const [images, videos] = await Promise.all([
    Promise.all((formValues.referenceImages ?? []).map(upload)),
    Promise.all((formValues.referenceVideo ?? []).map(upload)),
  ]);

  return { images, video: videos[0] ?? null };
}

// Shows the loading screen instead of the form until the scripts are ready.
// On an error the form comes back with its values and the error
const isGeneratingScripts = ref(false);

const handleContinue = handleSubmit(async (formValues) => {
  const currentAd = store.currentAd;
  const settings = buildVideoSettings(formValues);
  if (!store.currentSet || !currentAd || !settings) return;

  generalErrorMessage.value = undefined;

  // Re-priced on click, so what runs is what the button shows right now. The price can move
  // after it was shown without any setting changing: the quote learns from this ad set's last
  // real run, which another ad finishing updates (QAS 2026-10-29: the button said 27, the server
  // quoted 60 and charged 66). If it moved, show the new price and wait for another click
  const fresh = await VideoApi.estimateCost(
    settings,
    store.currentSet.id,
  ).catch(() => null);
  const freshCost = stepCostOf(fresh);
  if (freshCost === undefined) {
    // No price, no charge: the user is never charged for a step they weren't shown
    costEstimate.value = null;
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.video.settings.footer.price-unavailable",
    );
    return;
  }
  if (freshCost !== thisStepCost.value) {
    costEstimate.value = fresh;
    priceChangedTo.value = freshCost;
    return;
  }
  priceChangedTo.value = undefined;

  isGeneratingScripts.value = true;

  // Uploaded first, so no scripts are charged without them
  try {
    settings.external_references = {
      ...settings.external_references,
      ...(await uploadReferences(formValues)),
    };
  } catch (error) {
    console.error("Failed to upload the external references:", error);
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.video.settings.errors.references-upload-failed",
    );
    isGeneratingScripts.value = false;
    return;
  }

  try {
    const response = await VideoApi.generateScripts({
      id_adset: store.currentSet.id,
      ad_index: store.currentAdIndex,
      id_ad: currentAd.ad_id,
      brand_id: String(store.brandId),
      settings,
      custom_prompt: null,
      // TODO: send the concepts of the other ads of this ad set
      siblings: [],
    });

    // Generating the scripts was charged — show the new balance
    void refreshCredits();

    // The backend saves the scripts by itself, but not the settings. With the
    // channel and the variant count it also creates the variants of the ad
    // and marks them as video
    await VideoApi.saveDraft({
      ad_id: currentAd.ad_id,
      channel_id: store.currentChannel?.channel_id,
      variant_count: response.variants.length,
      settings,
    });

    // Load the saved draft and the new variants into the ad
    await store.refetchCurrentAd();

    store.setScreen("videoScripts");
  } catch (error) {
    console.error("Failed to generate video scripts:", error);
    // Out of credits / video limit / billing down get their own message
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    // Ran out between the estimate and the click: offer the way out, not just the error
    if (error instanceof InsufficientCreditsError)
      isAddCreditsOpen.value = true;
    generalErrorMessage.value = t(
      billingKey ??
        "funnel-flow.paid-social.ads.video.settings.errors.scripts-generation-failed",
    );
    isGeneratingScripts.value = false;
    return;
  }
});
</script>

<template>
  <!-- No stepper while generating. The form's values are kept on unmount -->
  <AdsAssemblyVideoGenerating v-if="isGeneratingScripts">
    <template #title>
      {{ $t("funnel-flow.paid-social.ads.video.generating.scripts.title") }}
    </template>

    <template #subtitle>
      {{
        $t("funnel-flow.paid-social.ads.video.generating.scripts.subtitle", {
          campaign: store.campaign.name,
        })
      }}
    </template>
  </AdsAssemblyVideoGenerating>

  <FormStepLayout v-else-if="store.currentSet" as="div" :maxWidth="910">
    <template #stepper>
      <AdsAssemblyVideoStepper :productionMode="generationMode" />
    </template>

    <!-- TODO: add help video URL later -->
    <PageTitle helpButton>
      {{ $t("funnel-flow.paid-social.ads.video.settings.title") }}

      <template #description>
        {{ $t("funnel-flow.paid-social.ads.video.settings.description") }}
      </template>
    </PageTitle>

    <AdsAssemblyVideoCreditAlert />

    <AdsAssemblySettingsCard icon="custom-rocket" iconVariant="info">
      <template #title>
        {{
          $t("funnel-flow.paid-social.ads.video.settings.auto-assembly.title")
        }}
      </template>

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.ads.video.settings.auto-assembly.description",
          )
        }}
      </template>

      <div class="tw:flex tw:flex-col tw:gap-4">
        <AdsAssemblySettingsOption
          :value="1"
          v-model="selectedVariations"
          icon="tabler:box-multiple"
        >
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.auto-assembly.option-1.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.auto-assembly.option-1.description",
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
                "funnel-flow.paid-social.ads.video.settings.auto-assembly.option-2.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.auto-assembly.option-2.description",
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
                "funnel-flow.paid-social.ads.video.settings.auto-assembly.option-3.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.auto-assembly.option-3.description",
                { count: store.currentSet.ads.length * 3 },
              )
            }}
          </template>
        </AdsAssemblySettingsOption>
      </div>
    </AdsAssemblySettingsCard>

    <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-6">
      <SegmentedToggle
        v-model="generationMode"
        :options="generationModeOptions"
      />

      <Separator />

      <div class="tw:flex tw:flex-col tw:gap-4">
        <AdsAssemblyVideoLabel icon="tabler:video">
          <template #title>
            {{
              $t("funnel-flow.paid-social.ads.video.settings.video-type.title")
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.video-type.description",
              )
            }}
          </template>
        </AdsAssemblyVideoLabel>

        <AdsAssemblySettingsOption value="CLASSIC_UGC_AI" v-model="videoType">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.video-type.classic-ugc-ai.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.video-type.classic-ugc-ai.description",
              )
            }}
          </template>
        </AdsAssemblySettingsOption>

        <AdsAssemblySettingsOption soon>
          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.video-type.soon-options",
              )
            }}
          </template>
        </AdsAssemblySettingsOption>
      </div>

      <template v-if="generationMode === 'FULL_VIDEO'">
        <Separator />

        <div class="tw:flex tw:flex-col tw:gap-4">
          <AdsAssemblyVideoLabel icon="tabler:atom">
            <template #title>
              {{ $t("funnel-flow.paid-social.ads.video.settings.model.title") }}
            </template>
          </AdsAssemblyVideoLabel>

          <div class="tw:grid tw:grid-cols-1 tw:gap-6 tw:xl:grid-cols-2">
            <div
              class="tw:relative tw:flex tw:aspect-video tw:items-center tw:justify-center tw:rounded-2xl tw:bg-gray-100"
            >
              <Icon
                icon="tabler:video"
                class="tw:text-[48px] tw:text-gray-500"
              />

              <span
                class="tw:absolute tw:bottom-5 tw:left-5 tw:font-medium tw:text-gray-700"
              >
                {{ selectedModel?.ui_name }}
              </span>
            </div>

            <div class="tw:flex tw:flex-col tw:gap-4">
              <FieldNewSelect
                name="model"
                :options="modelOptions"
                :clearable="false"
                hideLayout
              />

              <div
                class="tw:flex tw:flex-col tw:gap-4 tw:xl:flex-row tw:xl:items-center"
              >
                <FieldNewSelect
                  name="resolution"
                  :options="resolutionOptions"
                  hideLayout
                  class="tw:w-32"
                />

                <FieldNewSelect
                  name="format"
                  :options="FORMATS"
                  hideLayout
                  class="tw:w-28"
                />

                <FieldCheckbox
                  name="music"
                  class="tw:shrink-0"
                  :label="
                    $t('funnel-flow.paid-social.ads.video.settings.model.music')
                  "
                />
              </div>
            </div>
          </div>
        </div>
      </template>

      <Separator />

      <!-- Both modes, since Scripts Only can also have a voiceover -->
      <div
        class="tw:flex tw:flex-col tw:gap-4 tw:xl:flex-row tw:xl:items-center tw:xl:justify-between"
      >
        <AdsAssemblyVideoLabel icon="tabler:language">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.voice-accent.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.voice-accent.description",
              )
            }}
          </template>
        </AdsAssemblyVideoLabel>

        <FieldAutocomplete
          name="voiceAccent"
          :options="voiceAccentOptions"
          hideLayout
          class="tw:xl:basis-80"
        />
      </div>

      <Separator />

      <div class="tw:flex tw:flex-col tw:gap-4">
        <AdsAssemblyVideoLabel icon="tabler:file-search">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.external-references.title",
              )
            }}
          </template>

          <template #description>
            {{ referencesDescription }}
          </template>
        </AdsAssemblyVideoLabel>

        <Tabs v-model="referenceTab">
          <template #list>
            <Tab value="image" disableSaveLocking>
              {{
                $t(
                  "funnel-flow.paid-social.ads.video.settings.external-references.tabs.image",
                )
              }}
            </Tab>

            <Tab
              v-if="!isVideoReferenceHidden"
              value="video"
              disableSaveLocking
            >
              {{
                $t(
                  "funnel-flow.paid-social.ads.video.settings.external-references.tabs.video",
                )
              }}
            </Tab>
          </template>

          <TabsPanels>
            <TabPanel value="image">
              <FieldFiles
                name="referenceImages"
                :maxFiles="maxReferenceImages"
                :dropAreaLabel="
                  $t(
                    'funnel-flow.paid-social.ads.video.settings.external-references.images.drop-area-label',
                  )
                "
                size="sm"
                :maxSize="
                  ADS_ASSEMBLY_VIDEO_REFERENCE_IMAGE_MAX_FILE_SIZE_BYTES
                "
                :acceptedFormats="
                  ADS_ASSEMBLY_VIDEO_REFERENCE_IMAGE_ACCEPTED_FORMATS
                "
              />
            </TabPanel>

            <TabPanel v-if="!isVideoReferenceHidden" value="video">
              <FieldFiles
                name="referenceVideo"
                :maxFiles="1"
                :dropAreaLabel="
                  $t(
                    'funnel-flow.paid-social.ads.video.settings.external-references.video.drop-area-label',
                  )
                "
                size="sm"
                :maxSize="
                  ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_MAX_FILE_SIZE_BYTES
                "
                :acceptedFormats="
                  ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_ACCEPTED_FORMATS
                "
              />
            </TabPanel>
          </TabsPanels>
        </Tabs>

        <FieldTextarea
          name="referenceNotes"
          :label="
            $t(
              'funnel-flow.paid-social.ads.video.settings.external-references.notes-label',
            )
          "
          :placeholder="
            $t(
              'funnel-flow.paid-social.ads.video.settings.external-references.notes-placeholder',
            )
          "
          speechRecognition
          :rows="2"
        />
      </div>

      <Separator />

      <div class="tw:flex tw:flex-col tw:gap-4">
        <AdsAssemblyVideoLabel icon="tabler:clock">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.video-duration.title",
              )
            }}
          </template>

          <template #description>
            {{
              $t(
                "funnel-flow.paid-social.ads.video.settings.video-duration.description",
              )
            }}
          </template>
        </AdsAssemblyVideoLabel>

        <FieldSlider
          name="videoDuration"
          :label="
            $t(
              'funnel-flow.paid-social.ads.video.settings.video-duration.label',
            )
          "
          :min="MIN_VIDEO_DURATION_SECONDS"
          :max="MAX_VIDEO_DURATION_SECONDS"
          :format="formatVideoDuration"
          alwaysShowThumbLabel
        />
      </div>
    </CardBase>

    <AdsAssemblyVideoSettingsCreditEstimation :estimation="estimation" />

    <Alert v-if="priceChangedTo !== undefined" type="warning" autoScroll>
      {{
        $t("funnel-flow.paid-social.ads.video.settings.footer.price-changed", {
          cost: formatLucas(priceChangedTo),
        })
      }}
    </Alert>

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="handleGoBack" />

        <Button
          v-if="missingCredits > 0"
          leftIcon="tabler:shopping-cart"
          data-testid="video-settings-add-credits"
          @click="isAddCreditsOpen = true"
        >
          {{
            $t("funnel-flow.paid-social.ads.video.credits.add-credits.button")
          }}
        </Button>

        <Button
          v-else
          :disabled="thisStepCost === undefined"
          :isLoading="isSubmitting"
          @click="handleContinue"
        >
          {{
            $t("funnel-flow.paid-social.ads.video.settings.footer.continue", {
              // What pressing Continue charges (scripts + scoring), not the whole batch
              cost: formatLucas(thisStepCost),
            })
          }}
        </Button>
      </WizardCardActions>

      <AdsAssemblyVideoAddCreditsModal
        v-model="isAddCreditsOpen"
        :missing="missingCredits"
      />
    </template>

    <!-- Leaving with unsaved changes asks first -->
    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
