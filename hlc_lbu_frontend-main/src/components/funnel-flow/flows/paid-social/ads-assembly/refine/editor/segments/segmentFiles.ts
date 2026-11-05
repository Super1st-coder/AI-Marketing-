import type { FieldFilesBackendFile } from "@/components/forms/base/FieldFiles.vue";
import VideoApi, {
  VideoDraftVariant,
  VideoSegment,
  VideoVoiceoverClip,
} from "@/services/funnel-flow/paid-social/VideoApi";

/** A video the user picked and hasn't saved yet, or the storage key of a saved one. */
export type SegmentsFileValue = Blob | string | null;

/** A video the user uploaded, as `FieldFiles` shows it. */
export type SegmentsSavedFile = FieldFilesBackendFile & {
  storage_key: string;
};

/**
 * Opens a stored file in a new tab, with a fresh link from its storage key.
 * The tab is opened before the link is requested, since a tab opened after
 * waiting for a request isn't seen as coming from the click and gets blocked.
 */
export async function openStoredFile(storageKey: string) {
  const tab = window.open("", "_blank");
  if (!tab) {
    console.error("The browser blocked the tab for:", storageKey);
    return;
  }

  // The new tab can't reach back into the app
  tab.opener = null;

  try {
    tab.location.href = (await VideoApi.getDownloadUrl(storageKey)).url;
  } catch (error) {
    console.error("Failed to get the download URL:", error);
    tab.close();
  }
}

/**
 * Uploads a video the user picked. Kept forever, so it's only done when the
 * user saves.
 */
export async function uploadSegmentsVideo(file: Blob) {
  const upload =
    file instanceof File
      ? file
      : new File([file], "video.mp4", { type: file.type });

  const { data } = await VideoApi.uploadVideoAsset(upload);

  return {
    storage_key: data.storage_key,
    storage_path: data.storage_path,
    file_name: upload.name,
    file_size: upload.size,
  };
}

/** Why a shot's clip couldn't be generated. */
export type SegmentsClipFailure = "missing-frame" | "paused" | "unknown";

/**
 * Why a clip failed, from its shot's `error` in the generation job, which the
 * backend saves as `"<exception>: <message>"`. A shot whose storyboard frame
 * failed isn't generated or billed, and the ones held back after the provider
 * kept failing start with "held back".
 */
export function getClipFailure(error: string | null): SegmentsClipFailure {
  if (error?.startsWith("MissingStoryboardFrame")) return "missing-frame";
  if (error?.startsWith("held back")) return "paused";

  return "unknown";
}

/**
 * A link to a stored file that works for the backend: a fresh one from its
 * storage key, since the saved links expire within the hour.
 */
export async function getStoredFileUrl(file: {
  storage_key?: string | null;
  video_url?: string;
}) {
  return file.storage_key
    ? (await VideoApi.getDownloadUrl(file.storage_key)).url
    : (file.video_url ?? "");
}

/** One generated version of a shot's clip. */
export type SegmentsClipVersion = {
  clip: VideoSegment;
  /** The scene it was generated with. */
  scene: string;
};

/**
 * Every generated version of a shot's clip. The draft keeps one clip per
 * shot, so the history is kept here, like the storyboard's. The clips the
 * user uploaded aren't versions: they replace the generated one.
 */
export type SegmentsShotClipVersions = {
  /** Oldest first, so `v1` is at index 0. */
  history: SegmentsClipVersion[];
  /** Index in `history` of the clip the shot uses. */
  activeIndex: number;
};

/**
 * Why a shot's clip can't be edited: it uses a clip the user uploaded or
 * picked, which an edit would replace, or its storyboard image is missing in
 * a variant with a storyboard, so the clip would have nothing to start from.
 * A shot without a clip can be edited, like it can be retried.
 */
export type SegmentsShotEditLock = "uploaded" | "missing-frame";

/** What tells two clips apart: the stored file, or the provider's link. */
export function getClipKey(clip: VideoSegment) {
  return clip.storage_key ?? clip.video_url;
}

/**
 * Saves which clips and audio the variant's video was just assembled from, so the
 * editor knows when it's out of date after a reload. Not saving them only
 * leaves "Regenerate AI-edited video" enabled, so it doesn't fail the assembly.
 */
export async function saveVideoClipKeys(
  adId: number,
  variantId: string,
  orderedClips: VideoSegment[],
  /** The audio it was assembled with, in shot order. Scripts Only. */
  orderedAudio: VideoVoiceoverClip[] = [],
) {
  try {
    await VideoApi.saveDraft({
      ad_id: adId,
      variants: {
        [variantId]: {
          video_clip_keys: orderedClips.map(getClipKey),
          video_audio_keys: orderedAudio.map(getAudioKey),
        },
      },
    });
  } catch (error) {
    console.error("Failed to save the clips of the video:", error);
  }
}

/**
 * Whether the variant's video was assembled from other clips than the ones
 * it has now. `undefined` when it isn't known: a video assembled before the
 * clips were recorded.
 */
export function isVideoFromOtherClips(
  variant: VideoDraftVariant,
): boolean | undefined {
  const recorded = variant.video_clip_keys;
  if (!recorded) return undefined;

  const hasOtherClips = variant.shots.some((shot, index) => {
    const clip = variant.clips?.find((item) => item.shot_index === shot.index);
    return !clip || getClipKey(clip) !== recorded[index];
  });

  // Only compared when the video was assembled with audio
  const recordedAudio = variant.video_audio_keys ?? [];
  const hasOtherAudio =
    recordedAudio.length > 0 &&
    variant.shots.some((shot, index) => {
      const audio = variant.audio?.find(
        (item) => item.shot_index === shot.index,
      );
      return !audio || getAudioKey(audio) !== recordedAudio[index];
    });

  return hasOtherClips || hasOtherAudio;
}

/** What tells two audio clips apart: the stored file, or its link. */
export function getAudioKey(audio: VideoVoiceoverClip) {
  return audio.storage_key ?? audio.audio_url;
}
