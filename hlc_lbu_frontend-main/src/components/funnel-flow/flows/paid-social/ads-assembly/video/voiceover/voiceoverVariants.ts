import {
  GenerateVideoVoiceoverResponse,
  VideoDraftVariant,
  VideoVoice,
  VideoVoiceoverClip,
} from "@/services/funnel-flow/paid-social/VideoApi";

/** The audio generated for a variant, and the voice it was generated with. */
export type VoiceoverVariantAudio = {
  voice: VideoVoice;
  /** In shot order. A shot that failed has none. */
  clips: VideoVoiceoverClip[];
  /** `index` of the shots whose audio couldn't be generated. */
  failedShotIndexes: number[];
};

/** What the Voiceover step keeps for each variant. */
export type VoiceoverVariantState = {
  /** Whether its tab was opened. */
  visited: boolean;
  /** Generating the audio needs one. */
  selectedVoice: VideoVoice | null;
  /** Voices added from the search. Unlike the suggested ones, they can be removed. */
  addedVoices: VideoVoice[];
  /**
   * Null until generated. Generating it counts as reviewing the variant,
   * unless a shot failed.
   */
  audio: VoiceoverVariantAudio | null;
  isGenerating: boolean;
  errorMessage?: string;
};

/**
 * The voice ids of the speech saved in the drafts' audio, without repeats.
 * The draft keeps nothing else of the voice.
 */
export function getSavedVoiceIds(variants: VideoDraftVariant[]): string[] {
  return [
    ...new Set(
      variants.flatMap((variant) =>
        (variant.audio ?? [])
          .filter((clip) => clip.kind === "SPEECH" && clip.voice_id)
          .map((clip) => clip.voice_id),
      ),
    ),
  ];
}

/**
 * The state of a variant, with the audio saved in its draft if it has any. The
 * draft only keeps the `voice_id`, so the voice is looked for in the suggested
 * ones, then in the ones looked up by id (added from the search, or of another
 * accent). If it isn't in either, a voice with just its id stands in for it.
 */
export function createVoiceoverVariantState(
  variant: VideoDraftVariant,
  suggestedVoices: VideoVoice[],
  savedVoices: VideoVoice[],
): VoiceoverVariantState {
  const state: VoiceoverVariantState = {
    visited: false,
    selectedVoice: null,
    addedVoices: [],
    audio: null,
    isGenerating: false,
  };

  const clips = variant.audio ?? [];
  const voiceId = clips.find((clip) => clip.kind === "SPEECH")?.voice_id;
  if (!voiceId) return state;

  const suggestedVoice = suggestedVoices.find(
    (voice) => voice.voice_id === voiceId,
  );
  const voice = suggestedVoice ??
    savedVoices.find((item) => item.voice_id === voiceId) ?? {
      voice_id: voiceId,
      name: voiceId,
      accent: "",
      preview_url: "",
    };

  state.selectedVoice = voice;
  state.addedVoices = suggestedVoice ? [] : [voice];
  state.audio = {
    voice,
    clips,
    // Every shot gets audio, speech or room tone, and the backend only saves
    // the ones that worked, so a shot without a clip failed
    failedShotIndexes: variant.shots
      .filter((shot) => !clips.some((clip) => clip.shot_index === shot.index))
      .map((shot) => shot.index),
  };

  return state;
}

/**
 * The variant's audio from a `POST /video/voiceover` response. The request
 * succeeds even when some shots fail, so they're read from its progress.
 */
export function createVoiceoverVariantAudio(
  variantId: string,
  voice: VideoVoice,
  response: GenerateVideoVoiceoverResponse,
): VoiceoverVariantAudio {
  const shots =
    response.progress.variants.find(
      (variant) => variant.variant_id === variantId,
    )?.shots ?? [];

  return {
    voice,
    clips: response.audio[variantId] ?? [],
    failedShotIndexes: shots
      .filter((shot) => shot.status === "FAILED")
      .map((shot) => shot.index),
  };
}

/** The voices to pick from: the added ones first, then the suggested ones. */
export function getListedVoices(
  addedVoices: VideoVoice[],
  suggestedVoices: VideoVoice[],
): VideoVoice[] {
  return [
    ...addedVoices,
    ...suggestedVoices.filter(
      (voice) =>
        !addedVoices.some((added) => added.voice_id === voice.voice_id),
    ),
  ];
}

/**
 * The audio generated for a shot: its speech, or the room tone a shot with no
 * line gets instead.
 */
export function getShotClip(
  audio: VoiceoverVariantAudio | null,
  shotIndex: number,
): VideoVoiceoverClip | undefined {
  return audio?.clips.find((clip) => clip.shot_index === shotIndex);
}
