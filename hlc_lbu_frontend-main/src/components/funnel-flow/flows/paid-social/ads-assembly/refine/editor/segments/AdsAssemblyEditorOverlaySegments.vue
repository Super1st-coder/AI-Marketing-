<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, object } from "yup";
import { UnidentifiedError } from "@/services/common-errors";
import VideoApi, {
  VideoSegment,
  VideoVoiceoverClip,
} from "@/services/funnel-flow/paid-social/VideoApi";

import {
  SegmentsFileValue,
  SegmentsSavedFile,
  SegmentsShotClipVersions,
  SegmentsShotEditLock,
  getClipFailure,
  getClipKey,
  getStoredFileUrl,
  isVideoFromOtherClips,
  openStoredFile,
  saveVideoClipKeys,
  uploadSegmentsVideo,
} from "./segmentFiles";

// The clips of a video ad, and its final cut. Video flow only

const emit = defineEmits<{ exit: [] }>();

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();
const paidSocialFormStore = useFunnelPaidSocialFormStore();
const { refresh: refreshCredits } = useVideoCredits();
const notificationStore = useNotificationStore();

// The preview in the sidebar is the only other sign, and it's easy to miss
function showVideoUpdatedToast() {
  notificationStore.display({
    type: "success",
    title: t(
      "funnel-flow.paid-social.ads.refine.editor.segments.toasts.video-updated",
    ),
  });
}

// Only one voiceover plays at a time
useAudioPlayer();

const draftVariant = computed(() => store.currentVideoDraftVariant);

// The script doesn't change here, only the clips and the video
const variant = draftVariant.value;
if (!variant) {
  throw new UnidentifiedError();
}

const shots = variant.shots;
const settings = store.currentAd?.draft.settings ?? {};
const isScriptsOnly = settings.production_mode === "SCRIPTS_ONLY";

// Numbered like the variant tabs of the other steps
const variantNumber =
  Object.keys(store.currentAd?.draft.variants ?? {}).indexOf(
    variant.variant_id,
  ) + 1;

// The video model the clips are generated and edited with: Settings' one, or
// the default. Only shown and used to tell whether an edit can start from the
// current clip, so the screen still works without it
async function getVideoModel() {
  if (isScriptsOnly) return undefined;

  try {
    const { default: defaultId, models } = await VideoApi.getModels();
    const modelId = settings.model || defaultId;
    const model = models.find((item) => item.model_id === modelId);

    return {
      name: model?.ui_name ?? modelId,
      // Unknown counts as no: the backend drops a reference it can't use
      acceptsVideoReference: model?.accepts_video_reference === true,
    };
  } catch (error) {
    console.error("Failed to load the video models:", error);
    return settings.model
      ? { name: settings.model, acceptsVideoReference: false }
      : undefined;
  }
}

async function getVoiceName() {
  const voiceId = variant?.audio?.find(
    (clip) => clip.kind === "SPEECH",
  )?.voice_id;
  if (!isScriptsOnly || !voiceId) return undefined;

  try {
    const voice = await VideoApi.getVoice(voiceId);
    return voice.found ? voice.name : undefined;
  } catch (error) {
    console.error("Failed to load the voice:", error);
    return undefined;
  }
}

// The errors of the shots the last video generation couldn't make a clip for,
// by shot `index`. Read from its job, which expires after a day and is
// replaced by the next generation. Without it the shots just have no clip
async function getFailedClipErrors(): Promise<Record<number, string | null>> {
  const jobId = store.currentAd?.draft.jobs?.segments;
  if (isScriptsOnly || !jobId) return {};

  try {
    const job = await VideoApi.getJobProgress(jobId);
    const jobShots =
      job?.variants.find((item) => item.variant_id === variant?.variant_id)
        ?.shots ?? [];

    return Object.fromEntries(
      jobShots
        .filter((shot) => shot.status === "FAILED")
        .map((shot) => [shot.index, shot.error]),
    );
  } catch (error) {
    console.error("Failed to load the video generation job:", error);
    return {};
  }
}

const [videoModel, voiceName, failedClipErrors] = await Promise.all([
  getVideoModel(),
  getVoiceName(),
  getFailedClipErrors(),
]);

// The chip shows the model picked in Settings, as before
const modelName = settings.model ? videoModel?.name : undefined;

function getSavedClip(shotIndex: number) {
  return draftVariant.value?.clips?.find(
    (clip) => clip.shot_index === shotIndex,
  );
}

function getFrame(shotIndex: number) {
  return draftVariant.value?.frames?.find(
    (frame) => frame.shot_index === shotIndex,
  );
}

// A clip saved since then, uploaded or generated again, replaces the one that
// failed. In a variant with a storyboard, a shot whose frame is still missing
// can't be retried: the clip would ignore the direction the other shots follow.
// Once the frame is retried in the Storyboard step, the clip can be
function getShotClipFailure(shotIndex: number) {
  if (!(shotIndex in failedClipErrors) || getSavedClip(shotIndex)) {
    return undefined;
  }

  if (draftVariant.value?.frames?.length && !getFrame(shotIndex)) {
    return "missing-frame";
  }

  const failure = getClipFailure(failedClipErrors[shotIndex]);
  return failure === "missing-frame" ? "unknown" : failure;
}

// Shot `index` -> its generated versions. Only kept here, so they're lost
// when leaving the editor, like the storyboard's history
// TODO: keep them once the draft can hold more than one clip per shot
const clipVersions = ref<Record<number, SegmentsShotClipVersions>>({});

// The clip the draft has for each shot becomes its active version, added to
// its history when it's a new one: the first time, and after a retry or an
// edit. `scenes` has the scene the new ones were generated with. Uploaded
// clips aren't versions
function syncClipVersions(scenes: Record<number, string> = {}) {
  for (const shot of shots) {
    const clip = getSavedClip(shot.index);
    if (!clip || clip.uploaded) continue;

    const versions = (clipVersions.value[shot.index] ??= {
      history: [],
      activeIndex: 0,
    });
    const index = versions.history.findIndex(
      (version) => getClipKey(version.clip) === getClipKey(clip),
    );

    if (index === -1) {
      versions.history.push({ clip, scene: scenes[shot.index] ?? shot.scene });
      versions.activeIndex = versions.history.length - 1;
    } else {
      // The ad was loaded again, so it's the newest copy of the same clip
      versions.history[index].clip = clip;
      versions.activeIndex = index;
    }
  }
}

syncClipVersions();

// The shot whose clip is being generated again. One at a time, like the
// storyboard: each one is saved to the same draft
const retryingShotIndex = ref<number>();
const retryErrors = ref<Record<number, string>>({});
// Whether clips were retried, edited or picked from the history while the
// editor is open. Only used when the draft doesn't say which clips the video
// was assembled from, or for a final cut, which no clips are part of
const hasNewClips = ref(false);

// Billed as the shot's seconds. The clip starts from the shot's storyboard
// frame, like the first generation
async function handleRetryClip(shotIndex: number) {
  const ad = store.currentAd;
  const adSet = store.currentSet;
  const shotVariant = draftVariant.value ?? variant;
  if (!ad || !adSet || !shotVariant || retryingShotIndex.value !== undefined) {
    return;
  }

  retryingShotIndex.value = shotIndex;
  delete retryErrors.value[shotIndex];

  try {
    const frame = getFrame(shotIndex);
    await VideoApi.editSegmentShot({
      id_adset: adSet.id,
      ad_index: store.currentAdIndex,
      id_ad: ad.ad_id,
      brand_id: String(store.brandId),
      variant: shotVariant,
      shot_index: shotIndex,
      model: settings.model ?? null,
      scene_override: "",
      feedback: "",
      // The shot has no clip to start from
      current_video_url: null,
      // The provider downloads it, so the link has to be a fresh one
      image_url: frame ? await getStoredFileUrl(frame) : null,
    });
    void refreshCredits();

    hasNewClips.value = true;

    // Load the draft the backend saved the clip to
    await reloadSaved();

    // Generating a clip takes a while, so the user may be looking elsewhere.
    // The video isn't assembled with it: once every shot has a clip, the
    // toast says to regenerate it, like the hint under the button
    notificationStore.display({
      type: "success",
      title: t(
        "funnel-flow.paid-social.ads.refine.editor.segments.toasts.clip-retried",
        { number: shotIndex },
      ),
      description: canRegenerate.value
        ? t(
            "funnel-flow.paid-social.ads.refine.editor.segments.regenerate-video-outdated",
          )
        : undefined,
    });
  } catch (error) {
    console.error("Failed to retry the clip:", error);
    // Out of credits, billing down... get their own message
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    retryErrors.value[shotIndex] = t(
      billingKey ??
        "funnel-flow.paid-social.ads.refine.editor.segments.errors.retry-failed",
    );
  } finally {
    retryingShotIndex.value = undefined;
  }
}

// Scripts Only: the shot whose audio is being generated again. One at a time,
// like the clips: each one is saved to the same draft
const regeneratingAudioShotIndex = ref<number>();
const audioErrors = ref<Record<number, string>>({});
// Whether audio was regenerated while the editor is open. A video assembled
// without audio records none, so this is what tells it apart
const hasNewAudio = ref(false);

// The voice the variant's speech was generated with. A shot with no line gets
// room tone, which takes none
const variantVoiceId = computed(
  () =>
    draftVariant.value?.audio?.find((clip) => clip.kind === "SPEECH")
      ?.voice_id || undefined,
);

function getShotAudio(shotIndex: number) {
  return draftVariant.value?.audio?.find(
    (clip) => clip.shot_index === shotIndex,
  );
}

// Speech needs a voice, so a shot with a line can only be regenerated once
// the variant has one
function canRegenerateAudio(shotIndex: number) {
  const shot = shots.find((item) => item.index === shotIndex);
  return Boolean(
    shot &&
    (!shot.line?.trim() ||
      getShotAudio(shotIndex)?.voice_id ||
      variantVoiceId.value),
  );
}

// Billed by the line's characters. Same voice as the shot's audio, or the
// variant's when it has none, e.g. its audio failed
async function handleRegenerateAudio(shotIndex: number) {
  const ad = store.currentAd;
  const adSet = store.currentSet;
  const shotVariant = draftVariant.value ?? variant;
  if (
    !ad ||
    !adSet ||
    !shotVariant ||
    !canRegenerateAudio(shotIndex) ||
    isBusy.value
  ) {
    return;
  }

  regeneratingAudioShotIndex.value = shotIndex;
  delete audioErrors.value[shotIndex];

  try {
    await VideoApi.regenerateVoiceoverShot({
      id_adset: adSet.id,
      ad_index: store.currentAdIndex,
      id_ad: ad.ad_id,
      brand_id: String(store.brandId),
      variant: shotVariant,
      shot_index: shotIndex,
      voice_id: getShotAudio(shotIndex)?.voice_id || variantVoiceId.value || "",
    });
    void refreshCredits();

    // The video has the old audio until it's assembled again
    hasNewAudio.value = true;

    // Load the draft the backend saved the audio to
    await reloadSaved();

    notificationStore.display({
      type: "success",
      title: t(
        "funnel-flow.paid-social.ads.refine.editor.segments.toasts.audio-regenerated",
        { number: shotIndex },
      ),
      description: canRegenerate.value
        ? t(
            "funnel-flow.paid-social.ads.refine.editor.segments.regenerate-video-outdated",
          )
        : undefined,
    });
  } catch (error) {
    console.error("Failed to regenerate the audio:", error);
    // Out of credits, billing down... get their own message
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    audioErrors.value[shotIndex] = t(
      billingKey ??
        "funnel-flow.paid-social.ads.refine.editor.segments.errors.regenerate-audio-failed",
    );
  } finally {
    regeneratingAudioShotIndex.value = undefined;
  }
}

// The files the user uploaded are the form's values: the final cut as the
// list `FieldFiles` holds, the clips as their storage keys. The generated
// clips aren't values: they're shown, not edited
function getSavedValues() {
  const video = draftVariant.value?.video;
  const finalCut: SegmentsSavedFile[] =
    video?.final_cut && video.storage_key
      ? [
          {
            name: video.file_name ?? "",
            size: video.file_size,
            storage_key: video.storage_key,
          },
        ]
      : [];

  return {
    finalCut,
    clips: shots.map((shot) => {
      const clip = getSavedClip(shot.index);
      return clip?.uploaded && clip.storage_key ? clip.storage_key : null;
    }),
  };
}

const savedValues = ref(getSavedValues());

// The format and size are checked before a file is picked (by `FieldFiles`
// and the shot's upload), so the values are always valid
const fileSchema = mixed<Blob | string>().nullable();

const schema = toTypedSchema(
  object({
    finalCut: array().of(mixed<File | SegmentsSavedFile>().required()),
    clips: array().of(fileSchema).required(),
  }),
);

const { handleSubmit, isSubmitting, meta, values, resetForm, resetField } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: savedValues.value,
  });

type SegmentsValues = {
  /** The final cut: picked, saved or none. `FieldFiles` holds it as a list. */
  finalCut: File | SegmentsSavedFile | null;
  clips: SegmentsFileValue[];
};

// The form's values are typed as partial objects, but the files are kept as
// they were picked
function getValues(): SegmentsValues {
  return {
    finalCut:
      (values.finalCut?.[0] as File | SegmentsSavedFile | undefined) ?? null,
    clips: ((values.clips ?? []) as (SegmentsFileValue | undefined)[]).map(
      (clip) => clip ?? null,
    ),
  };
}

const pickedFinalCut = computed(() => {
  const finalCut = values.finalCut?.[0];
  return finalCut instanceof File ? finalCut : undefined;
});

const isUploadingFinalCut = ref(false);
const isRegenerating = ref(false);
const isExiting = ref(false);
const isBusy = computed(
  () =>
    isSubmitting.value ||
    isUploadingFinalCut.value ||
    isRegenerating.value ||
    isSavingVersion.value ||
    retryingShotIndex.value !== undefined ||
    regeneratingAudioShotIndex.value !== undefined,
);

const generalErrorMessage = ref<string>();

function haveClipsChanged(current: SegmentsValues) {
  return current.clips.some(
    (clip, index) => clip !== savedValues.value.clips[index],
  );
}

// Assembling needs a clip for every shot. A generated clip counts unless the
// user replaced it with one they then removed
function hasEveryClip(current: SegmentsValues) {
  return shots.every((shot, index) => {
    if (current.clips[index]) return true;

    const saved = getSavedClip(shot.index);
    return Boolean(saved && !saved.uploaded);
  });
}

// Retrying, editing or picking a clip from the history doesn't assemble the
// video, so it needs assembling when its clips aren't the shots' ones anymore.
// The draft says which clips it was assembled from, so it's known after a
// reload too
const isVideoOutdated = computed(() => {
  const current = draftVariant.value;
  if (!current?.video) return true;
  if (current.video.final_cut) return hasNewClips.value || hasNewAudio.value;

  return (
    (isVideoFromOtherClips(current) ?? hasNewClips.value) || hasNewAudio.value
  );
});

const canRegenerate = computed(() => {
  const current = getValues();
  return (
    (haveClipsChanged(current) || isVideoOutdated.value) &&
    hasEveryClip(current)
  );
});

// Replaces the clips of the shots the user changed: the picked files are
// uploaded, and the uploaded clips that were removed are dropped
async function saveClips(clipValues: SegmentsFileValue[]) {
  const ad = store.currentAd;
  if (!ad || !variant) throw new UnidentifiedError();

  const clips = (
    await Promise.all(
      shots.map(async (shot, index): Promise<VideoSegment | undefined> => {
        const value = clipValues[index];
        const saved = getSavedClip(shot.index);

        if (value instanceof Blob) {
          const file = await uploadSegmentsVideo(value);

          return {
            shot_index: shot.index,
            video_url: file.storage_path,
            duration_s: shot.end_s - shot.start_s,
            storage_key: file.storage_key,
            storage_path: file.storage_path,
            uploaded: true,
            file_name: file.file_name,
            file_size: file.file_size,
          };
        }

        if (!value && saved?.uploaded) return undefined;

        return saved;
      }),
    )
  ).filter((clip) => clip !== undefined);

  await VideoApi.saveDraft({
    ad_id: ad.ad_id,
    variants: { [variant.variant_id]: { clips } },
  });

  return clips;
}

/** Saving kept the changed clips, but the video couldn't be assembled from them. */
class VideoAssemblyError extends Error {
  constructor() {
    super("VIDEO_ASSEMBLY_FAILED");
    this.name = this.constructor.name;
  }
}

// Joins the clips into the video, which the backend saves to the draft
async function assemble(clips: VideoSegment[]) {
  const ad = store.currentAd;
  const adSet = store.currentSet;
  if (!ad || !adSet || !variant) throw new UnidentifiedError();

  const orderedClips = shots.map((shot) =>
    clips.find((clip) => clip.shot_index === shot.index),
  );
  if (orderedClips.some((clip) => !clip)) throw new UnidentifiedError();

  // Scripts Only adds the voiceover, one per shot or none. In Full Video it's
  // already in the clips
  const audio = isScriptsOnly
    ? shots.map((shot) =>
        draftVariant.value?.audio?.find(
          (clip) => clip.shot_index === shot.index,
        ),
      )
    : [];
  const hasEveryAudio = audio.every((clip) => clip?.storage_key);

  const [clipUrls, audioUrls] = await Promise.all([
    Promise.all(orderedClips.map((clip) => getStoredFileUrl(clip!))),
    hasEveryAudio
      ? Promise.all(audio.map((clip) => getStoredFileUrl(clip!)))
      : Promise.resolve([]),
  ]);

  await VideoApi.assembleVideo({
    id_adset: adSet.id,
    ad_index: store.currentAdIndex,
    id_ad: ad.ad_id,
    variant: draftVariant.value ?? variant,
    clip_urls: clipUrls,
    audio_urls: audioUrls,
    music_url: null,
    burn_subtitles: false,
    variant_row_id: store.currentVariant?.id,
  });

  // So the video is known to be up to date until its clips or audio change
  await saveVideoClipKeys(
    ad.ad_id,
    variant.variant_id,
    orderedClips as VideoSegment[],
    audioUrls.length ? (audio as VideoVoiceoverClip[]) : [],
  );
}

// Sets the uploaded final cut as the variant's video, instead of the
// assembled one
async function saveFinalCut(finalCut: Blob) {
  const ad = store.currentAd;
  if (!ad || !variant) throw new UnidentifiedError();

  const file = await uploadSegmentsVideo(finalCut);

  await VideoApi.saveDraft({
    ad_id: ad.ad_id,
    variants: {
      [variant.variant_id]: {
        video: {
          video_url: file.storage_path,
          storage_key: file.storage_key,
          storage_path: file.storage_path,
          final_cut: true,
          file_name: file.file_name,
          file_size: file.file_size,
        },
      },
    },
  });
}

async function reloadSaved() {
  await store.refetchCurrentAd();
  await paidSocialFormStore.revalidate();
  savedValues.value = getSavedValues();
  syncClipVersions();
}

// Clip editing: the shot's generated versions, opened from its "Edit shot"
const isShotModalOpen = ref(false);
/** `index` of the shot the modal opens on. */
const shotModalInitialIndex = ref<number>();
const shotModalErrorMessage = ref<string>();
const isSavingVersion = ref(false);

function handleEditShot(shotIndex: number) {
  shotModalInitialIndex.value = shotIndex;
  shotModalErrorMessage.value = undefined;
  isShotModalOpen.value = true;
}

// An edit saves the new clip over the shot's one, so uploading or picking a
// clip locks it. A shot without a clip can be edited, like it can be retried,
// except when its storyboard image is missing, for the same reason as Retry
const shotEditLocks = computed(() => {
  const clipValues = getValues().clips;

  return Object.fromEntries(
    shots.flatMap((shot, index): [number, SegmentsShotEditLock][] => {
      const saved = getSavedClip(shot.index);
      if (clipValues[index] !== null || saved?.uploaded) {
        return [[shot.index, "uploaded"]];
      }

      if (
        !saved &&
        draftVariant.value?.frames?.length &&
        !getFrame(shot.index)
      ) {
        return [[shot.index, "missing-frame"]];
      }

      return [];
    }),
  );
});

// Picking a version doesn't consume credits. The draft keeps one clip per
// shot, so the shot's one is replaced with it
async function handleSelectClipVersion(
  shotIndex: number,
  versionIndex: number,
) {
  const ad = store.currentAd;
  const versions = clipVersions.value[shotIndex];
  const version = versions?.history[versionIndex];
  if (
    !ad ||
    !variant ||
    !version ||
    versionIndex === versions.activeIndex ||
    isBusy.value
  ) {
    return;
  }

  const previousIndex = versions.activeIndex;
  versions.activeIndex = versionIndex;
  shotModalErrorMessage.value = undefined;
  isSavingVersion.value = true;

  try {
    const clips = shots.flatMap((shot) => {
      const clip =
        shot.index === shotIndex ? version.clip : getSavedClip(shot.index);
      return clip ? [clip] : [];
    });

    await VideoApi.saveDraft({
      ad_id: ad.ad_id,
      variants: { [variant.variant_id]: { clips } },
    });

    // Enables "Regenerate AI-edited video", like an edit
    hasNewClips.value = true;
    await reloadSaved();
  } catch (error) {
    console.error("Failed to save the selected clip:", error);
    versions.activeIndex = previousIndex;
    shotModalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.refine.editor.segments.shot-modal.errors.select-failed",
    );
  } finally {
    isSavingVersion.value = false;
  }
}

// The edit modal already loaded the draft the backend saved the clip to
async function handleClipEdited(shotIndex: number, scene: string) {
  void refreshCredits();
  // The video isn't assembled with it: "Regenerate AI-edited video" is
  // enabled instead, so the user decides when
  hasNewClips.value = true;
  shotModalErrorMessage.value = undefined;

  savedValues.value = getSavedValues();
  syncClipVersions({ [shotIndex]: scene });
  await paidSocialFormStore.revalidate();

  notificationStore.display({
    type: "success",
    title: t(
      "funnel-flow.paid-social.ads.refine.editor.segments.toasts.shot-updated",
      { number: shotIndex },
    ),
    // Like the retry toast: the hint only applies once the video can be regenerated
    description: canRegenerate.value
      ? t(
          "funnel-flow.paid-social.ads.refine.editor.segments.regenerate-video-outdated",
        )
      : undefined,
  });
}

/**
 * Saves everything pending, like pressing the buttons below the preview: the
 * changed clips replace the saved ones, then a picked final cut becomes the
 * video. Without one, the clips are assembled into it, as long as every shot
 * has a clip.
 */
async function save(current: SegmentsValues) {
  const ad = store.currentAd;
  if (!ad || !variant) throw new UnidentifiedError();

  const clipsChanged = haveClipsChanged(current);
  const isFinalCutRemoved =
    current.finalCut === null && savedValues.value.finalCut.length > 0;
  const canAssemble = hasEveryClip(current);

  const clips = clipsChanged
    ? await saveClips(current.clips)
    : (draftVariant.value?.clips ?? []);
  let isAssemblyFailed = false;

  if (current.finalCut instanceof File) {
    await saveFinalCut(current.finalCut);
  } else if (current.finalCut === null && (clipsChanged || isFinalCutRemoved)) {
    if (canAssemble) {
      try {
        await assemble(clips);
        hasNewClips.value = false;
        hasNewAudio.value = false;
      } catch (error) {
        console.error("Failed to assemble the video:", error);
        // The clips are saved by now, so the video is behind them and can be
        // regenerated from the button
        if (clipsChanged) hasNewClips.value = true;
        isAssemblyFailed = true;
      }
    } else if (isFinalCutRemoved) {
      // Nothing to assemble instead of the removed final cut
      await VideoApi.saveDraft({
        ad_id: ad.ad_id,
        variants: { [variant.variant_id]: { video: null } },
      });
    }
  }

  await reloadSaved();
  resetForm({ values: savedValues.value });

  // After the reset, so the saved clips don't stay pending in the form
  if (isAssemblyFailed) throw new VideoAssemblyError();
}

const onSubmit = handleSubmit(async () => {
  generalErrorMessage.value = undefined;

  try {
    await save(getValues());

    // Otherwise only the button turning disabled says so. "Save & Exit" only
    // submits when there's something to save, and closes the editor
    notificationStore.display({
      type: "success",
      title: t(
        "funnel-flow.paid-social.ads.refine.editor.segments.toasts.changes-saved",
      ),
    });

    return true;
  } catch (error) {
    console.error("Failed to save the segments:", error);
    generalErrorMessage.value = t(
      error instanceof VideoAssemblyError
        ? "funnel-flow.paid-social.ads.refine.editor.segments.errors.regenerate-video-failed"
        : "funnel-flow.paid-social.ads.refine.editor.segments.errors.save-failed",
    );
    return false;
  }
});

async function handleSaveAndExit() {
  isExiting.value = true;

  try {
    if (meta.value.dirty && (await onSubmit()) !== true) return;
    emit("exit");
  } finally {
    isExiting.value = false;
  }
}

async function handleUploadFinalCut() {
  const finalCut = pickedFinalCut.value;
  if (!finalCut) return;

  isUploadingFinalCut.value = true;
  generalErrorMessage.value = undefined;

  try {
    await saveFinalCut(finalCut);
    await reloadSaved();
    resetField("finalCut", { value: savedValues.value.finalCut });
  } catch (error) {
    console.error("Failed to upload the final cut:", error);
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.refine.editor.segments.errors.upload-final-cut-failed",
    );
  } finally {
    isUploadingFinalCut.value = false;
  }
}

async function handleRegenerate() {
  if (!canRegenerate.value) return;

  isRegenerating.value = true;
  generalErrorMessage.value = undefined;

  try {
    await assemble(await saveClips(getValues().clips));
    hasNewClips.value = false;
    hasNewAudio.value = false;
    await reloadSaved();
    resetField("clips", { value: savedValues.value.clips });

    // The assembled video replaced the final cut. One the user picked and
    // hasn't uploaded is kept
    if (!pickedFinalCut.value) {
      resetField("finalCut", { value: savedValues.value.finalCut });
    }

    showVideoUpdatedToast();
  } catch (error) {
    console.error("Failed to regenerate the video:", error);
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.refine.editor.segments.errors.regenerate-video-failed",
    );
  } finally {
    isRegenerating.value = false;
  }
}

// The picked final cut shows instead of the saved video. A saved final cut the
// user removed doesn't show, since saving drops it
const pickedFinalCutSrc = useObjectUrl(pickedFinalCut);
const { src: savedVideoSrc, refresh: refreshSavedVideoSrc } = useStoredFileSrc(
  () => {
    const video = draftVariant.value?.video;
    if (!video || (video.final_cut && !values.finalCut?.length)) return;

    return { storage_key: video.storage_key, storage_url: video.storage_path };
  },
);
const previewSrc = computed(() =>
  pickedFinalCut.value ? pickedFinalCutSrc.value : savedVideoSrc.value,
);

// A picked final cut's link doesn't expire, only the saved video's does
function handlePreviewError() {
  if (!pickedFinalCut.value) refreshSavedVideoSrc();
}

const isDownloadingScript = ref(false);

// The backend writes the script, so it's the same one the asset package has.
// It comes as text, so it's saved as a file instead of opened in a tab
async function handleDownloadScript() {
  if (!variant) return;

  isDownloadingScript.value = true;
  generalErrorMessage.value = undefined;

  try {
    const { root, documents } = await VideoApi.getScriptPackage({
      variant: draftVariant.value ?? variant,
      campaign: store.campaign.name,
      ad_index: store.currentAdIndex,
      variant_index: variantNumber,
      production_mode: settings.production_mode ?? "FULL_VIDEO",
      // The Settings step's default
      duration_s: settings.target_duration_s ?? 30,
    });

    const script = documents["script.txt"];
    if (script === undefined) throw new UnidentifiedError();

    // The campaign name can have characters a file name can't
    const fileName = `${root} - script.txt`.replace(/[\\/:*?"<>|]/g, "-");
    downloadBlob(new Blob([script], { type: "text/plain" }), fileName);
  } catch (error) {
    console.error("Failed to download the script:", error);
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.ads.refine.editor.segments.errors.download-script-failed",
    );
  } finally {
    isDownloadingScript.value = false;
  }
}

// README, script, edited video, and every saved frame, clip and voiceover
const assetCount = computed(() => {
  const current = draftVariant.value;
  const storedCount = [
    ...(current?.frames ?? []),
    ...(current?.clips ?? []),
    ...(current?.audio ?? []),
  ].filter((file) => file.storage_key).length;

  return 2 + (current?.video?.storage_key ? 1 : 0) + storedCount;
});
</script>

<template>
  <!-- The content grows, so the footer stays at the bottom of the screen -->
  <form class="tw:flex tw:grow tw:flex-col" @submit.prevent="onSubmit">
    <Container :maxWidth="1088" class="tw:grow tw:py-8">
      <div class="tw:flex tw:flex-col tw:gap-6">
        <!-- Header -->
        <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-6">
          <div
            class="tw:flex tw:flex-col tw:gap-4 tw:lg:flex-row tw:lg:items-start tw:lg:justify-between"
          >
            <!-- Requirements -->
            <div class="tw:flex tw:flex-col tw:gap-2">
              <!-- Title -->
              <h3 class="tw:font-bold">
                {{
                  $t(
                    "funnel-flow.paid-social.ads.refine.editor.segments.requirements",
                  )
                }}
              </h3>

              <!-- Chips -->
              <div class="tw:flex tw:flex-wrap tw:gap-3">
                <Chip color="secondary" variant="outlined" size="md">
                  {{
                    $t(
                      "funnel-flow.paid-social.ads.refine.editor.segments.aspect-ratio",
                    )
                  }}
                </Chip>

                <Chip
                  v-if="draftVariant?.video?.has_subtitles"
                  color="secondary"
                  variant="outlined"
                  size="md"
                >
                  {{
                    $t(
                      "funnel-flow.paid-social.ads.refine.editor.segments.embed-subtitles",
                    )
                  }}
                </Chip>

                <Chip
                  v-if="settings.target_duration_s"
                  color="secondary"
                  variant="outlined"
                  size="md"
                  leftIcon="tabler:clock"
                >
                  {{
                    $t(
                      "funnel-flow.paid-social.ads.refine.editor.segments.duration",
                      { seconds: settings.target_duration_s },
                    )
                  }}
                </Chip>

                <Chip
                  v-if="modelName"
                  color="secondary"
                  variant="outlined"
                  size="md"
                  leftIcon="tabler:atom"
                >
                  {{ modelName }}
                </Chip>
              </div>
            </div>

            <!-- Actions -->
            <div class="tw:flex tw:flex-wrap tw:items-center tw:gap-4">
              <Button
                color="secondary"
                variant="outlined"
                size="sm"
                type="button"
                leftIcon="tabler:download"
                :uppercase="false"
                :isLoading="isDownloadingScript"
                @click="handleDownloadScript"
              >
                {{
                  $t(
                    "funnel-flow.paid-social.ads.refine.editor.segments.download-script",
                  )
                }}
              </Button>

              <!-- TODO: enable once the backend can build the zip -->

              <Button
                variant="label"
                size="sm"
                type="button"
                leftIcon="tabler:download"
                :uppercase="false"
                disabled
              >
                {{
                  $t(
                    "funnel-flow.paid-social.ads.refine.editor.segments.download-all-assets",
                    { count: assetCount },
                  )
                }}
              </Button>

              <Tooltip placement="top" :maxWidth="280">
                <button
                  type="button"
                  class="tw:flex tw:text-2xl tw:text-secondary-text"
                  :aria-label="
                    $t(
                      'funnel-flow.paid-social.ads.refine.editor.segments.download-all-assets-tooltip',
                    )
                  "
                >
                  <Icon icon="tabler:info-circle" aria-hidden="true" />
                </button>

                <template #content>
                  {{
                    $t(
                      "funnel-flow.paid-social.ads.refine.editor.segments.download-all-assets-tooltip",
                    )
                  }}
                </template>
              </Tooltip>
            </div>
          </div>

          <!-- Final cut upload -->
          <!-- Removing the saved one only drops it from the value: saving
            replaces the video -->
          <FieldFiles
            name="finalCut"
            :maxFiles="1"
            :maxSize="ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_MAX_FILE_SIZE_BYTES"
            :acceptedFormats="
              ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_ACCEPTED_FORMATS
            "
            orientation="horizontal"
            browseButton
            :dropAreaLabel="
              $t(
                'funnel-flow.paid-social.ads.refine.editor.segments.upload-final-cut',
              )
            "
            :getBackendFileSrc="(_file: SegmentsSavedFile) => savedVideoSrc"
            :disabled="isBusy"
          >
            <template #dropAreaDescription>
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.editor.segments.upload-final-cut-description",
                  { number: variantNumber },
                )
              }}
            </template>
          </FieldFiles>
        </CardBase>

        <!-- General alert -->
        <Alert v-if="generalErrorMessage" type="error" autoScroll>
          {{ generalErrorMessage }}
        </Alert>

        <!-- Shots and sidebar with preview -->
        <div
          class="tw:flex tw:flex-col tw:items-start tw:gap-15 tw:lg:flex-row"
        >
          <!-- Shots -->
          <div class="tw:flex tw:w-full tw:min-w-0 tw:flex-col tw:gap-4">
            <AdsAssemblyEditorOverlaySegmentsShot
              v-for="(shot, index) in shots"
              :key="shot.index"
              :shot="shot"
              :fieldIndex="index"
              :isScriptsOnly="isScriptsOnly"
              :savedClip="getSavedClip(shot.index)"
              :audioClip="
                isScriptsOnly
                  ? draftVariant?.audio?.find(
                      (clip) => clip.shot_index === shot.index,
                    )
                  : undefined
              "
              :voiceName="voiceName"
              :failure="getShotClipFailure(shot.index)"
              :editLock="shotEditLocks[shot.index]"
              :isRetrying="retryingShotIndex === shot.index"
              :retryErrorMessage="retryErrors[shot.index]"
              @retry="handleRetryClip(shot.index)"
              @editShot="handleEditShot(shot.index)"
              :canRegenerateAudio="canRegenerateAudio(shot.index)"
              :isRegeneratingAudio="regeneratingAudioShotIndex === shot.index"
              :audioErrorMessage="audioErrors[shot.index]"
              @regenerateAudio="handleRegenerateAudio(shot.index)"
              :frame="
                draftVariant?.frames?.find(
                  (frame) => frame.shot_index === shot.index,
                )
              "
              :disabled="isBusy"
            />
          </div>

          <!-- Sidebar -->
          <div
            class="tw:flex tw:w-full tw:max-w-[318px] tw:shrink-0 tw:flex-col tw:gap-4 tw:lg:basis-[318px]"
          >
            <!-- Preview -->
            <AdPreviewFromData
              v-if="store.currentVariant"
              :media="store.currentVariant.media"
              :channel_attributes="store.currentVariant.channel_attributes"
              :videoSrc="previewSrc"
              aspectRatio="auto"
              size="lg"
              @videoError="handlePreviewError"
            >
              <template v-if="!previewSrc" #media>
                <div
                  class="tw:flex tw:aspect-[9/16] tw:items-center tw:justify-center"
                >
                  <Icon
                    icon="tabler:video-off"
                    class="tw:text-[48px] tw:text-gray-500"
                    aria-hidden="true"
                  />
                </div>
              </template>
            </AdPreviewFromData>

            <Button
              variant="label"
              size="sm"
              type="button"
              leftIcon="tabler:download"
              :uppercase="false"
              :disabled="!draftVariant?.video?.storage_key"
              @click="openStoredFile(draftVariant!.video!.storage_key!)"
            >
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.editor.segments.download-video",
                )
              }}
            </Button>

            <Button
              color="secondary"
              variant="outlined"
              size="sm"
              type="button"
              leftIcon="tabler:upload"
              :uppercase="false"
              :disabled="!pickedFinalCut || isBusy"
              :isLoading="isUploadingFinalCut"
              @click="handleUploadFinalCut"
            >
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.editor.segments.upload-final-cut",
                )
              }}
            </Button>

            <div class="tw:flex tw:flex-col tw:gap-2">
              <Button
                color="secondary"
                variant="outlined"
                size="sm"
                type="button"
                leftIcon="tabler:refresh"
                :uppercase="false"
                :disabled="!canRegenerate || isBusy"
                :isLoading="isRegenerating"
                @click="handleRegenerate"
              >
                {{
                  $t(
                    "funnel-flow.paid-social.ads.refine.editor.segments.regenerate-video",
                  )
                }}
              </Button>

              <p class="tw:text-center tw:text-sm tw:text-secondary-text">
                {{
                  hasEveryClip(getValues())
                    ? $t(
                        isVideoOutdated
                          ? "funnel-flow.paid-social.ads.refine.editor.segments.regenerate-video-outdated"
                          : "funnel-flow.paid-social.ads.refine.editor.segments.regenerate-video-hint",
                      )
                    : $t(
                        "funnel-flow.paid-social.ads.refine.editor.segments.regenerate-video-missing-clips",
                      )
                }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Container>

    <AdsAssemblyEditorOverlayFooter>
      <Button
        variant="label"
        type="submit"
        :uppercase="false"
        :disabled="!meta.dirty || (isBusy && !isSubmitting) || isExiting"
        :isLoading="isSubmitting && !isExiting"
      >
        {{ $t("funnel-flow.paid-social.ads.refine.editor.save-changes") }}
      </Button>

      <Button
        type="button"
        :uppercase="false"
        :disabled="isBusy && !isExiting"
        :isLoading="isExiting"
        @click="handleSaveAndExit"
      >
        {{
          $t("funnel-flow.paid-social.ads.refine.editor.segments.save-and-exit")
        }}
      </Button>
    </AdsAssemblyEditorOverlayFooter>

    <!-- Save locking: leaving discards the changes, or asks first while they're
      saving -->
    <ModalFormSaveAlert :isDirty="meta.dirty || isBusy" />

    <!-- Teleported, so its form isn't inside this one -->
    <AdsAssemblyEditorOverlaySegmentsShotModal
      v-if="
        isShotModalOpen && shotModalInitialIndex !== undefined && draftVariant
      "
      v-model="isShotModalOpen"
      :variant="draftVariant"
      :clipVersions="clipVersions"
      :locks="shotEditLocks"
      :initialShotIndex="shotModalInitialIndex"
      :modelId="settings.model ?? null"
      :modelName="videoModel?.name"
      :acceptsVideoReference="videoModel?.acceptsVideoReference ?? false"
      :isBusy="isBusy"
      :errorMessage="shotModalErrorMessage"
      @selectVersion="handleSelectClipVersion"
      @applied="handleClipEdited"
    />
  </form>
</template>
