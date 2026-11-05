import { handleCommonErrors } from "../../common-errors";

// Enums
export type VideoProductionMode = "SCRIPTS_ONLY" | "FULL_VIDEO";

export const VIDEO_SHOT_DELIVERY_MODES = [
  "ON_CAMERA",
  "VOICEOVER",
  "SILENT",
] as const;
export type VideoShotDeliveryMode = (typeof VIDEO_SHOT_DELIVERY_MODES)[number];

/** How a shot is framed. The camera, not what happens in it. */
export const VIDEO_SHOT_TYPES = [
  "SELFIE_HANDHELD",
  "TALKING_HEAD_MEDIUM",
  "UNBOXING",
  "PRODUCT_CLOSEUP",
  "MIRROR_SELFIE",
  "LIFESTYLE_ACTION",
  "BEFORE_AFTER_SPLIT",
  "WALK_AND_TALK",
  "REACTION_SHOT",
] as const;
export type VideoShotType = (typeof VIDEO_SHOT_TYPES)[number];

export type VideoScriptDiversityAxis =
  "emocion" | "intencion" | "visual_dominante" | "contexto_uso" | "psicologia";

export type VideoScriptShot = {
  index: number;
  start_s: number;
  end_s: number;
  delivery_mode: VideoShotDeliveryMode;
  shot_type: VideoShotType;
  emotion: string;
  line: string;
  scene: string;
  composition: string;
  /** Whether the real product appears in the shot, so its photo is used. */
  shows_product: boolean;
  on_screen_text: string;
};

export type VideoScriptAndromedaScores = {
  resonancia: number;
  autenticidad: number;
  claridad: number;
  marca: number;
  accion: number;
  rationale: string;
};

/** The fixed look of a variant, reused by every shot so it stays consistent. */
export type VideoScriptStyleAnchor = {
  /** The protagonist: age, hair, eyes, wardrobe, distinctive features. */
  character_sheet: string;
  /** The product itself: color, material, distinctive features. */
  product_sheet: string;
  /** Where the product exists at its real size, e.g. "indoors, in an ordinary room". */
  product_setting: string;
  /** The single setting of the ad. */
  location: string;
  lighting: string;
  lens: string;
  palette: string[];
  /** How every spoken line sounds, e.g. "neutral Latin American Spanish". */
  voice: string;
  /** The protagonist doesn't change clothes mid-ad. */
  wardrobe_lock: boolean;
  /** Shared generation seed, 100000-999999. */
  seed: number | null;
};

export type VideoScriptVariant = {
  variant_id: string;
  title: string;
  axis: VideoScriptDiversityAxis;
  archetype: string;
  strategic_angle: string;
  hook: string;
  /** The complication that keeps the viewer watching between hook and solution. */
  cliffhanger: string;
  final_cta: string;
  shots: VideoScriptShot[];
  persona: string;
  /** 0-10. Null when the variant couldn't be scored. */
  score: number | null;
  andromeda: VideoScriptAndromedaScores | null;
  /** Null for scripts generated before the anchor existed. */
  style_anchor: VideoScriptStyleAnchor | null;
  score_outdated: boolean;
};

export type VideoType =
  | "CLASSIC_UGC_AI"
  | "COMMERCIAL"
  | "PRODUCT_INTEGRATION"
  | "SUPER_CRAZY"
  | "VIRAL_COPYCAT"
  | "CUSTOM"
  | "DIRECT_TESTIMONIAL"
  | "UNBOXING_DEMO"
  | "BEFORE_AFTER"
  | "FOUNDER_STORY"
  | "MEME_TREND"
  | "EDUCATIONAL_HOWTO";

export type VideoModel = {
  model_id: string;
  ui_name: string;
  provider: string;
  max_clip_s: number | null;
  /** e.g. `["720p", "1080p"]`. Varies per model. */
  resolutions: string[];
  native_audio: boolean;
  accepts_video_reference: boolean | null;
  max_reference_images: number | null;
  notes: string;
  unverified: string[];
  /** False when the credits registry can't price it. It can't be selected. */
  billable: boolean;
};

export type VideoExternalReferences = {
  /** Stored references to uploaded images. */
  images: string[];
  /** One stored video reference, up to 60s. */
  video: string | null;
  replicate_notes: string;
};

/** Generation settings sent with `POST /video/scripts`. */
export type VideoSettings = {
  /** Ads to generate for the ad set, 1-50. */
  ads_count: number;
  /** Variants per ad, 1-10. */
  variants_per_ad: number;
  production_mode: VideoProductionMode;
  video_type: VideoType;
  /** Full Video only. */
  model: string | null;
  resolution: string | null;
  output_format: string;
  music: boolean;
  /** `"en"`, `"es"`, or empty to follow the ad set context. */
  language: string;
  /** ElevenLabs accent code, e.g. `"latin american"`. Not the UI label. */
  voice_accent: string;
  /** 8-120. */
  target_duration_s: number;
  external_references: VideoExternalReferences;
  /** Set by the "Is the content ready?" modal, Scripts Only only. */
  storyboard_enabled: boolean | null;
  voiceover_enabled: boolean | null;
};

export type VideoJobShotStatus = "PENDING" | "GENERATING" | "READY" | "FAILED";

/** One shot's slot in a generation job. */
export type VideoJobShotState = {
  index: number;
  status: VideoJobShotStatus;
  /** URL once `READY`. */
  artifact: string | null;
  error: string | null;
  updated_at: number;
};

/**
 * Per-shot progress of a generation job. `complete` means nothing is still
 * moving, not that everything succeeded: check `failed_shots` for that.
 */
export type VideoJobProgress = {
  job_id: string;
  stage: "storyboard" | "voiceover" | "video" | "captions" | null;
  /** `"redis"`, or `"memory"` when Redis is unreachable. */
  backend: string;
  totals: Record<string, number>;
  complete: boolean;
  failed_shots: number;
  variants: {
    variant_id: string;
    shots: VideoJobShotState[];
  }[];
  meta: Record<string, unknown>;
};

/** One 9:16 storyboard frame. */
export type VideoStoryboardFrame = {
  shot_index: number;
  /** Signed link that expires within the hour, same as `storage_path`. */
  image_url: string;
  /** Omitted by default, the model name is never surfaced. */
  model?: string | null;
  /** Signed link the browser can show directly. Null when it couldn't be stored. */
  storage_path?: string | null;
  /**
   * Permanent reference to the stored frame. Keep this one, and get a fresh
   * link from it with `POST /storage/video/{account_id}/download-url`.
   */
  storage_key?: string | null;
};

/** The languages the voice catalogue supports. Any other one is rejected. */
export const VIDEO_VOICE_LANGUAGES = ["es", "en"] as const;
export type VideoVoiceLanguage = (typeof VIDEO_VOICE_LANGUAGES)[number];

/** One generated clip of a shot. */
export type VideoSegment = {
  shot_index: number;
  /** The provider's own link, which is temporary. */
  video_url: string;
  duration_s: number;
  /** Omitted by default, the model name is never surfaced. */
  model?: string | null;
  /**
   * Signed link the browser can play directly. Expires within the hour, so
   * don't keep it. Null when the clip couldn't be stored.
   */
  storage_path?: string | null;
  /**
   * Permanent reference to the stored clip. Keep this one, and get a fresh
   * link from it with `POST /storage/video/{account_id}/download-url`.
   */
  storage_key?: string | null;
  /**
   * Set by the frontend on a clip the user uploaded instead of the generated
   * one, with the file's name and size to show it. The backend never sets it.
   */
  uploaded?: boolean;
  file_name?: string;
  file_size?: number;
};

/**
 * How the clips are kept consistent: chained to the previous clip when the
 * model takes a video reference, starting each shot from the last frame of the
 * previous one when it takes an image, anchored on the storyboard frame when it
 * takes neither.
 */
export type VideoSegmentsContinuity =
  "previous-clip" | "last-frame" | "storyboard-frame";

/** One voice of the catalogue. */
export type VideoVoice = {
  voice_id: string;
  name: string;
  /**
   * The provider's own accent code, as it reports it, e.g. `"es-mexican"`.
   * Not normalised like `GetVideoVoicesResponse.accents`.
   */
  accent: string;
  /**
   * Static MP3. Auditioning plays it and is free: never generate audio to
   * preview a voice. Empty when the provider has none.
   */
  preview_url: string;
};

/** `GET /video/voices/{voice_id}`. The fields are empty when it isn't found. */
export type GetVideoVoiceResponse = VideoVoice & {
  /** False when no voice has the id, for example if the provider removed it. */
  found: boolean;
  language: string;
};

/** `AMBIENT` is the room tone a shot with no line gets instead of speech. */
export type VideoVoiceoverClipKind = "SPEECH" | "AMBIENT";

/** One shot's generated audio. */
export type VideoVoiceoverClip = {
  shot_index: number;
  audio_url: string;
  kind: VideoVoiceoverClipKind;
  /** Empty for `AMBIENT` clips. */
  voice_id: string;
  /**
   * Signed link the browser can play directly. Expires within the hour, so
   * don't keep it. Null when the clip couldn't be stored.
   */
  storage_path: string | null;
  /**
   * Permanent reference to the stored clip. Keep this one, and get a fresh
   * link from it with `POST /storage/video/{account_id}/download-url`.
   */
  storage_key: string | null;
};

/**
 * What is saved for one variant: its script, with what each later step adds
 * under its own key. The backend merges one level deep per variant, so a step
 * never erases the others.
 */
export type VideoDraftVariant = VideoScriptVariant & {
  /** Added by the storyboard step. */
  frames?: VideoStoryboardFrame[];
  /**
   * The frame every other shot of the variant copies the protagonist from:
   * the first shot framed on a person. Added by the storyboard step. Missing
   * when the variant has no person, or that shot's frame failed.
   * Signed link, expires within the hour.
   */
  anchor_url?: string;
  /** Permanent reference to `anchor_url`, to get a fresh link. */
  anchor_key?: string;
  /**
   * The visual direction applied to the frames, if any. Saved by the frontend:
   * the backend only keeps the frames it generated.
   */
  visual_direction?: string;
  /** Added by the voiceover step. */
  audio?: VideoVoiceoverClip[];
  /** Added by the video step. */
  clips?: VideoSegment[];
  /**
   * Added by the assemble step, or the final cut the user uploaded instead.
   * Null once a final cut is removed and there's nothing to assemble.
   */
  video?: VideoDraftAssembledVideo | null;
  /**
   * The clips `video` was assembled from, in shot order, by `storage_key` (or
   * `video_url` without one). Saved by the frontend after each assembly, so a
   * video whose clips changed since is known to be out of date, even after a
   * reload. Missing on videos assembled before it existed.
   */
  video_clip_keys?: string[];
  /**
   * The audio `video` was assembled with, like `video_clip_keys`. Scripts
   * Only, empty when it was assembled without it.
   */
  video_audio_keys?: string[];
};

/**
 * What the draft keeps of a finished video. The storage fields are left out
 * when the video couldn't be stored. A final cut the user uploaded only has
 * its storage fields, and what the frontend saves to show it.
 */
export type VideoDraftAssembledVideo = Partial<
  Pick<
    AssembleVideoResponse,
    | "video_url"
    | "duration_s"
    | "shot_count"
    | "has_audio"
    | "has_subtitles"
    | "has_music"
    | "storage_path"
    | "storage_key"
  >
> & {
  /** Set by the frontend on a final cut the user uploaded. */
  final_cut?: boolean;
  file_name?: string;
  file_size?: number;
};

/** The progress saved for one ad, so a refresh costs nothing. */
export type VideoDraft = {
  ad_id: number;
  /** False the first time, when nothing was saved yet. It isn't an error. */
  exists: boolean;
  /** Empty until saved. */
  settings: Partial<VideoSettings>;
  /**
   * Keyed by the script's `variant_id` (`"v1"`, `"v2"`...), as saved by the
   * generation endpoints when they get the `id_ad`. Never has entries removed,
   * only replaced.
   */
  variants: Record<string, VideoDraftVariant>;
  /**
   * The last step saved: `"scripts"`, `"storyboard"` or `"voiceover"`. Not a
   * screen name. Empty until saved.
   */
  current_step: string;
  /** Step -> id of the job that paid for it. The auto-save leaves it empty. */
  jobs: Record<string, string>;
  /** The ad-channel rows of the variants, in order. Same as `variant_rows`. */
  variant_ids: number[];
  /**
   * Script `variant_id` (`"v1"`...) -> its ad-channel row id, the id the
   * reviewed flags take. Empty until `POST /draft` creates the rows.
   */
  variant_rows: Record<string, number>;
};

/** The steps with a reviewed flag per variant. The Ad step has none. */
export type VideoReviewStage = "scripts" | "storyboard" | "voiceover";

export type MarkVideoVariantReviewedRequest = {
  /** Ad-channel row id, from `VideoDraft.variant_rows`. */
  variant_id: number;
  stage: VideoReviewStage;
};

export type MarkVideoVariantReviewedResponse = {
  variant_id: number;
  flag: "reviewed";
  value: boolean;
  /** False when storing it failed. The request doesn't fail for that. */
  saved: boolean;
};

export type GetVideoVariantReviewStatusRequest = {
  /** Ad-channel row ids, at least one. */
  variant_ids: number[];
  stage: VideoReviewStage;
};

export type GetVideoVariantReviewStatusResponse = {
  stage: VideoReviewStage;
  /** The row ids not reviewed yet, in the order sent. */
  pending: number[];
  all_reviewed: boolean;
};

/** A concept already used by another ad of the same ad set. */
export type VideoAdConcept = {
  ad_index: number;
  axis: VideoScriptDiversityAxis;
  archetype: string;
  hook: string;
};

// API Request types
export type GenerateVideoScriptsRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /**
   * Ad id. With it the backend saves the scripts to the ad's draft by itself.
   * Without it they're generated and billed but not kept.
   */
  id_ad: number;
  /** Tenant charged for the generation. Optional while scripts aren't billed. */
  brand_id: string;
  settings: VideoSettings;
  /** Extra creative direction. */
  custom_prompt: string | null;
  /** Concepts used by the other ads of the ad set, so each ad comes out different. */
  siblings: VideoAdConcept[];
};

export type ScoreVideoScriptsRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Tenant charged for the generation. Optional while scripts aren't billed. */
  brand_id: string;
  /** The edited variants. Each one is scored on its own. */
  variants: VideoScriptVariant[];
};

export type GenerateVideoStoryboardRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /**
   * Ad id. With it the backend saves the frames to the ad's draft by itself.
   * Without it they're generated and billed but not kept.
   */
  id_ad: number;
  /** Brand whose licence is charged. */
  brand_id: string;
  variants: VideoScriptVariant[];
  /** Anchors the protagonist. Every shot uses the same one. */
  base_image_url: string | null;
  /** `variant_id` -> visual direction already applied. */
  visual_directions: Record<string, string>;
};

/**
 * A visual direction for one variant. Shared by `validate-direction`, which is
 * free, and `apply-direction`, which regenerates every frame and is billed.
 */
export type VideoVisualDirectionRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /**
   * Ad id. With it, applying the direction saves the new frames to the ad's
   * draft by itself. Ignored when validating.
   */
  id_ad: number;
  /** Brand whose licence is charged. Only needed to apply. */
  brand_id: string;
  direction: string;
  variant: VideoScriptVariant;
  /** The other variants of the ad, since diversity is judged across them. */
  siblings: VideoScriptVariant[];
  /**
   * `variant_id` -> fresh link to the frame the variant's protagonist is
   * copied from, so applying the direction keeps the same person. The backend
   * can't refresh the saved one when it has expired. Missing, the variant
   * picks its anchor again. Only used to apply.
   */
  variant_anchors?: Record<string, string>;
};

/** The "Edit Shot" modal for one storyboard frame. */
export type EditVideoStoryboardShotRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /**
   * Ad id. With it the backend saves the new frame to the ad's draft by
   * itself. Without it it's generated and billed but not kept.
   */
  id_ad: number;
  /** Brand whose licence is charged. */
  brand_id: string;
  variant: VideoScriptVariant;
  /** `index` of the shot, 1-based. */
  shot_index: number;
  /** Replaces the shot's scene. Empty keeps it. */
  scene_override: string;
  feedback: string;
  /** Image-to-image off `current_image_url`, keeps the character identical. */
  use_current_as_reference: boolean;
  current_image_url: string | null;
  base_image_url: string | null;
};

/** One clip per shot, for every variant sent. Full Video only. Billed. */
export type GenerateVideoSegmentsRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /**
   * Ad id. With it the backend saves the clips to the ad's draft by itself.
   * Without it they're generated and billed but not kept.
   */
  id_ad: number;
  /** Brand whose licence is charged. */
  brand_id: string;
  variants: VideoScriptVariant[];
  /** Video model id. The default one when null. */
  model: string | null;
  /**
   * The resolution saved in the ad's Settings. Sent explicitly, with the model, so the
   * charge uses exactly what the price window priced. When null the backend reads the ad's
   * draft, then its own default.
   */
  resolution: string | null;
  /**
   * `variant_id` -> shot `index` -> frame URL. On models that take no video
   * reference, they're what keeps the protagonist the same between shots.
   */
  storyboard_frames: Record<string, Record<number, string>>;
  /** `variant_id` -> visual direction already applied. */
  visual_directions: Record<string, string>;
};

/** One shot's clip, generated again. Full Video only. Billed. */
export type EditVideoSegmentShotRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /**
   * Ad id. With it the backend saves the clip to the ad's draft by itself,
   * replacing the shot's one. Without it it's generated and billed but not
   * kept.
   */
  id_ad: number;
  /** Brand whose licence is charged. */
  brand_id: string;
  variant: VideoScriptVariant;
  /** `index` of the shot, 1-based. */
  shot_index: number;
  /** Video model id. The default one when null. */
  model: string | null;
  /** Replaces the shot's scene. Empty keeps it. */
  scene_override: string;
  feedback: string;
  /**
   * The clip being edited, so the new one is a variation of it. Models that
   * take no video reference use `image_url` instead.
   */
  current_video_url: string | null;
  /** The shot's storyboard frame. The provider downloads it. */
  image_url: string | null;
};

/**
 * The new clip. The draft also gets its storage key, but the response
 * doesn't have it, so it's read from the draft.
 */
export type EditVideoSegmentShotResponse = {
  variant_id: string;
  shot_index: number;
  video_url: string;
  duration_s: number;
  qty_real: number;
  unit: string;
  model_id: string;
  action: string;
  /** E.g. the model couldn't use the clip as a reference. */
  notes: string[];
  /**
   * Whether the clip was saved to the ad's draft. False doesn't mean the
   * generation failed, it was billed: it just wasn't kept.
   */
  draft_saved: boolean;
};

/**
 * The documents of one variant's asset package: its README and its script.
 * Free, nothing is generated.
 */
export type GetScriptPackageRequest = {
  variant: VideoScriptVariant;
  /** Campaign name. Starts the package's name. */
  campaign: string;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /** Numbered like the variant tabs, 1-based. */
  variant_index: number;
  production_mode: VideoProductionMode;
  /** 8-120. */
  duration_s: number;
  storyboard_enabled?: boolean;
  voiceover_enabled?: boolean;
  /** Whether the shots have clips yet. */
  has_video_assets?: boolean;
};

export type GetScriptPackageResponse = {
  /** The package's folder name: "{campaign} - Ad {n} - Variante {m}". */
  root: string;
  folders: { name: string; files: string[]; description: string }[];
  /** File name -> its text: `README.txt` and `script.txt`. */
  documents: Record<string, string>;
  file_count: number;
};

/** Joins one variant's clips into the finished video. Free. */
export type AssembleVideoRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /**
   * Ad id. With it the backend saves the video to the ad's draft by itself.
   * Without it the video is assembled but not kept.
   */
  id_ad: number;
  variant: VideoScriptVariant;
  /** In shot order. At least one. */
  clip_urls: string[];
  /**
   * One per clip, or none. Empty in Full Video, where the audio is already in
   * the clips.
   */
  audio_urls: string[];
  music_url: string | null;
  /**
   * Burns the subtitles into the video, which can't be undone. The subtitle
   * file is generated either way.
   */
  burn_subtitles: boolean;
  /**
   * The variant's ad-channel row (`VideoDraft.variant_rows`). With it the
   * backend marks the variant as having its media, which publishing needs.
   */
  variant_row_id?: number;
};

/**
 * Saves part of the progress. Only what is sent is written, so each step can
 * save without knowing about the others.
 */
export type SaveVideoDraftRequest = {
  ad_id: number;
  /**
   * The channel the variants are created in (`AdChannelDefinition.channel_id`,
   * Meta Ads). With `variant_count`, creates the variants of the ad in it,
   * which is what makes them selectable and publishable. Existing ones are kept.
   */
  channel_id?: number;
  variant_count?: number;
  settings?: Partial<VideoSettings>;
  variants?: Record<string, Partial<VideoDraftVariant>>;
  current_step?: string;
  jobs?: Record<string, string>;
};

/** Query of `GET /video/voices`, the Language -> Accent -> Voice cascade. */
export type GetVideoVoicesRequest = {
  language: VideoVoiceLanguage;
  /**
   * Accent code from `GetVideoVoicesResponse.accents`, e.g. `"mexican"`. Not
   * the UI label, which matches no voice. Empty for the language's default.
   */
  accent?: string;
  /** Filters `results` by name. */
  search?: string;
};

/** Audio for every shot of the variants sent. */
export type GenerateVideoVoiceoverRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /**
   * Ad id. With it the backend saves the audio to the ad's draft by itself.
   * Without it it's generated and billed but not kept.
   */
  id_ad: number;
  /**
   * Wallet the Lucas are drawn from. Sinergia fills it in from the session,
   * so leave it out: an empty value isn't replaced and the request fails.
   */
  org_id?: string;
  /** Tenant whose Lucas balance is charged. */
  brand_id: string;
  variants: VideoScriptVariant[];
  /** `variant_id` -> chosen `voice_id`. Required for every variant sent. */
  voice_ids: Record<string, string>;
};

/** One shot's audio, generated again. Billable. */
export type RegenerateVideoVoiceoverShotRequest = {
  /** Sinergia ad set id. */
  id_adset: number;
  /** Which ad of the ad set, 1-based. */
  ad_index: number;
  /**
   * Ad id. With it the backend saves the audio to the ad's draft by itself,
   * replacing the shot's one. Without it it's generated and billed but not
   * kept.
   */
  id_ad: number;
  /**
   * Wallet the Lucas are drawn from. Sinergia fills it in from the session,
   * so leave it out: an empty value isn't replaced and the request fails.
   */
  org_id?: string;
  /** Tenant whose Lucas balance is charged. */
  brand_id: string;
  variant: VideoScriptVariant;
  /** `index` of the shot, 1-based. */
  shot_index: number;
  /** Required when the shot has a line. */
  voice_id: string;
};

// API Response types
export type GetVideoModelsResponse = {
  /** `model_id` of the default model. */
  default: string;
  models: VideoModel[];
};

export type GenerateVideoScriptsResponse = {
  job_id: string;
  id_adset: number;
  ad_index: number;
  production_mode: VideoProductionMode;
  requested_duration_s: number;
  planned_shots: number;
  variants: VideoScriptVariant[];
  warnings: string[];
  /**
   * Whether the scripts were saved to the ad's draft. False doesn't mean the
   * generation failed, it was billed: they just weren't kept.
   */
  draft_saved: boolean;
};

export type ScoreVideoScriptsResponse = {
  job_id: string;
  id_adset: number;
  variants: VideoScriptVariant[];
  warnings: string[];
};

export type GenerateVideoStoryboardResponse = {
  job_id: string;
  id_adset: number;
  ad_index: number;
  progress: VideoJobProgress;
  /** `variant_id` -> frames, in shot order. */
  frames: Record<string, VideoStoryboardFrame[]>;
  /**
   * Whether the frames were saved to the ad's draft. False doesn't mean the
   * generation failed, it was billed: they just weren't kept.
   */
  draft_saved: boolean;
};

/** `WARNING` when the direction reduces the creative diversity of the ad. */
export type VideoVisualDirectionVerdict = "OK" | "WARNING";

export type ValidateVideoVisualDirectionResponse = {
  verdict: VideoVisualDirectionVerdict;
  /** The copy to show for the verdict, in English. */
  banner: string;
  /** Why, for debugging. Not shown. */
  reason: string;
  /** Always false: a warning never prevents applying the direction. */
  blocks: boolean;
};

/** A new version of the frame. Nothing is overwritten. */
export type EditVideoStoryboardShotResponse = {
  variant_id: string;
  shot_index: number;
  image_url: string;
  /** The scene the frame was generated with. */
  scene: string;
  used_reference: boolean;
  qty_real: number;
  unit: string;
  model_id: string;
  /** Signed link to the stored frame, expires within the hour. */
  storage_path: string | null;
  /** Permanent reference to the stored frame. Null if it couldn't be stored. */
  storage_key: string | null;
  /**
   * Whether the frame was saved to the ad's draft. False doesn't mean the
   * generation failed, it was billed: it just wasn't kept.
   */
  draft_saved: boolean;
};

export type GenerateVideoSegmentsResponse = {
  job_id: string;
  id_adset: number;
  ad_index: number;
  continuity: VideoSegmentsContinuity;
  progress: VideoJobProgress;
  /**
   * `variant_id` -> clips, in shot order. A shot that failed has none, and
   * the request still succeeds: check `progress.failed_shots`.
   */
  segments: Record<string, VideoSegment[]>;
  /**
   * Whether the clips were saved to the ad's draft. False doesn't mean the
   * generation failed, it was billed: they just weren't kept.
   */
  draft_saved: boolean;
};

export type AssembleVideoResponse = {
  variant_id: string;
  /** Where the video sits on the backend. Not playable in the browser. */
  video_url: string;
  duration_s: number;
  shot_count: number;
  has_audio: boolean;
  has_subtitles: boolean;
  has_music: boolean;
  /** True when a stand-in produced it. Never a real deliverable. */
  is_placeholder: boolean;
  /**
   * Signed link the browser can play directly. Expires within the hour, so
   * don't keep it. Null when the video couldn't be stored.
   */
  storage_path: string | null;
  /** Permanent reference to the stored video. Keep this one. */
  storage_key: string | null;
  /** Always false, assembling is free. */
  billable: boolean;
  /** E.g. why the video couldn't be stored. */
  notes: string[];
  /**
   * Whether the video was saved to the ad's draft. False doesn't mean the
   * assembly failed: the video exists, it just wasn't kept.
   */
  draft_saved: boolean;
};

/** A fresh link to a file stored in the video bucket. */
export type VideoAssetDownloadUrl = {
  bucket: string;
  key: string;
  /** Signed link the browser, or fal, can fetch directly. */
  url: string;
  /** Seconds the link works for. */
  expires_in: number;
};

/** A file uploaded to the video bucket, e.g. an external reference. */
export type UploadVideoAssetResponse = {
  ok: boolean;
  data: {
    /** Permanent reference to the file. Keep this one. */
    storage_key: string;
    /** Signed link to the file. Expires after `expires_in` seconds. */
    storage_path: string;
    expires_in: number;
  };
};

export type GetVideoVoicesResponse = {
  language: VideoVoiceLanguage;
  /** The accent the voices are for. The default one when none was sent. */
  accent: string;
  default_accent: string;
  /** Accent codes available in the language. */
  accents: string[];
  /** The most popular voices of the accent, most popular first. */
  suggested: VideoVoice[];
  /** Every voice of the accent, filtered by `search` when sent. */
  results: VideoVoice[];
  tts_model: string;
};

export type GenerateVideoVoiceoverResponse = {
  job_id: string;
  id_adset: number;
  ad_index: number;
  progress: VideoJobProgress;
  /**
   * `variant_id` -> clips, in shot order. A shot that failed has none, and
   * the request still succeeds: check `progress.failed_shots`.
   */
  audio: Record<string, VideoVoiceoverClip[]>;
  /**
   * Whether the audio was saved to the ad's draft. False doesn't mean the
   * generation failed, it was billed: it just wasn't kept.
   */
  draft_saved: boolean;
};

export type RegenerateVideoVoiceoverShotResponse = VideoVoiceoverClip & {
  variant_id: string;
  qty_real: number;
  unit: string;
  model_id: string;
  /**
   * Whether the audio was saved to the ad's draft. False doesn't mean the
   * generation failed, it was billed: it just wasn't kept.
   */
  draft_saved: boolean;
};

/**
 * The company's Luca Credits wallet (amounts in LUCA; 100 LUCA = $1). The company is resolved
 * by Sinergia from the session — the same wallet every video call is charged to.
 */
export type VideoCreditsBalance = {
  org_id: string;
  /** Spendable now (granted − used − reserved). */
  available: number;
  /** Total credits granted (license + purchased). */
  granted: number;
  used: number;
  /** Held by generations still running. */
  reserved: number;
  /** Fraction 0–1, used / granted (0.79 = 79%). Use `useVideoCredits().usagePct` for a %. */
  usage_pct: number;
  /** Video-generation spend so far, against `video_cap` (LUCA). */
  video_spend: number;
  video_cap: number;
  license: number;
  purchased: number;
  /** "Buy more credits" link, when configured. */
  topup_url: string | null;
};

/** One billable step of a batch, as the credits service priced it. */
export type VideoCostEstimateLine = {
  /** `video_scripts`, `video_andromeda_score`, `video_storyboard`, `video_segment`… */
  action: string;
  model_id: string;
  /** Tokens, images or seconds, depending on `unit`. */
  qty: number;
  unit: string;
  /** Whole LUCA, rounded up per line like the real charge. */
  lucas: number;
  /** False when the registry has no price for this step yet. */
  priced: boolean;
  note: string;
};

/** What a batch will cost before anything is generated. Free: holds and charges nothing. */
export type VideoCostEstimate = {
  lines: VideoCostEstimateLine[];
  total_lucas: number;
  /** False when a step couldn't be priced, so `total_lucas` is a minimum. */
  complete: boolean;
  note: string;
};

/**
 * One step's cost. `priced` false means it couldn't be priced: show "—", never 0.
 * `applies` false means this production mode never charges the step (voiceover in Full
 * Video, video in Scripts Only), so it costs nothing.
 */
export type VideoStepCost = {
  lucas: number;
  priced: boolean;
  applies: boolean;
};

/**
 * What the next step costs for variants that already exist, priced per shot exactly as each
 * step is charged: storyboard (one image per shot), voiceover (the spoken characters, Scripts
 * Only) and video (the rendered seconds of every shot, Full Video).
 */
export type VideoVariantsEstimate = {
  variants: {
    variant_id: string;
    storyboard: VideoStepCost;
    voiceover: VideoStepCost;
    video: VideoStepCost;
  }[];
  storyboard: VideoStepCost;
  voiceover: VideoStepCost;
  video: VideoStepCost;
  /** Re-scoring these variants after an edit; the charge is capped at this + 10%. */
  rescore: VideoStepCost;
  /**
   * The scene rewrite "Apply Changes" runs before regenerating the frames, when a direction
   * was sent (HL-2751). Its charge is capped at this + 10%.
   */
  direction?: VideoStepCost;
};

// Served by Fury through the Sinergia passthrough
const BASE_URL = "/v2/application/hiluca/video";

export default {
  async getBalance(): Promise<VideoCreditsBalance> {
    try {
      return await $api<VideoCreditsBalance>(`${BASE_URL}/balance`, {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  /**
   * `idAdset` lets the estimate count this ad set's real prompts (brand context included)
   * instead of fixed averages, so the quote matches the charge for every brand.
   */
  async estimateCost(
    settings: VideoSettings,
    idAdset?: number,
  ): Promise<VideoCostEstimate> {
    try {
      return await $api<VideoCostEstimate>(`${BASE_URL}/estimate`, {
        method: "POST",
        body: { settings, id_adset: idAdset ?? null },
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  /**
   * The real cost of the next step for these variants, for the windows that ask before
   * generating. Free: it writes no ledger entry and holds nothing.
   */
  async estimateVariants(
    variants: VideoScriptVariant[],
    productionMode: VideoProductionMode,
    model?: string | null,
    /** The ad set, so the re-scoring price uses its real scoring prompt. */
    idAdset?: number | null,
    /** A visual direction about to be applied: also prices its scene rewrite. */
    direction?: string | null,
    /**
     * The ad, so the video is priced at the resolution saved in its Settings, as /segments
     * renders and charges it. Without it the price uses the server default (768P).
     */
    idAd?: number | null,
    /**
     * The resolution saved in the ad's Settings, sent explicitly like `/segments` sends it,
     * so the window prices exactly what the video will render and charge.
     */
    resolution?: string | null,
  ): Promise<VideoVariantsEstimate> {
    try {
      return await $api<VideoVariantsEstimate>(
        `${BASE_URL}/estimate/variants`,
        {
          method: "POST",
          body: {
            variants,
            production_mode: productionMode,
            model: model ?? null,
            id_adset: idAdset ?? null,
            direction: direction ?? null,
            id_ad: idAd ?? null,
            resolution: resolution ?? null,
          },
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getModels(): Promise<GetVideoModelsResponse> {
    try {
      return await $api<GetVideoModelsResponse>(`${BASE_URL}/models`, {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateScripts(
    body: GenerateVideoScriptsRequest,
  ): Promise<GenerateVideoScriptsResponse> {
    try {
      return await $api<GenerateVideoScriptsResponse>(`${BASE_URL}/scripts`, {
        method: "POST",
        body,
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async scoreScripts(
    body: ScoreVideoScriptsRequest,
  ): Promise<ScoreVideoScriptsResponse> {
    try {
      return await $api<ScoreVideoScriptsResponse>(
        `${BASE_URL}/scripts/score`,
        {
          method: "POST",
          body,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Billed, and only responds once every frame is generated
  async generateStoryboard(
    body: GenerateVideoStoryboardRequest,
  ): Promise<GenerateVideoStoryboardResponse> {
    try {
      return await $api<GenerateVideoStoryboardResponse>(
        `${BASE_URL}/storyboard`,
        {
          method: "POST",
          body,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Billed. Generates a new version of one frame, nothing is overwritten
  async editStoryboardShot(
    body: EditVideoStoryboardShotRequest,
  ): Promise<EditVideoStoryboardShotResponse> {
    try {
      return await $api<EditVideoStoryboardShotResponse>(
        `${BASE_URL}/storyboard/edit-shot`,
        {
          method: "POST",
          body,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // "Validate with Luca". Free, nothing is generated
  async validateVisualDirection(
    body: VideoVisualDirectionRequest,
  ): Promise<ValidateVideoVisualDirectionResponse> {
    try {
      return await $api<ValidateVideoVisualDirectionResponse>(
        `${BASE_URL}/storyboard/validate-direction`,
        {
          method: "POST",
          body,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Billed. Regenerates every frame of the variant, and only responds once
  // they're all done. Frames that failed are missing from the response
  async applyVisualDirection(
    body: VideoVisualDirectionRequest,
  ): Promise<GenerateVideoStoryboardResponse> {
    try {
      return await $api<GenerateVideoStoryboardResponse>(
        `${BASE_URL}/storyboard/apply-direction`,
        {
          method: "POST",
          body,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Billed per second of video, and only responds once every clip is done.
  // Answers 503 `VIDEO_GENERATION_DISABLED` while video generation is off
  async generateSegments(
    body: GenerateVideoSegmentsRequest,
  ): Promise<GenerateVideoSegmentsResponse> {
    try {
      return await $api<GenerateVideoSegmentsResponse>(`${BASE_URL}/segments`, {
        method: "POST",
        body,
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Uploads a file the user picked, kept forever under `uploads/`. Up to 64 MB.
  // The backend takes the account from the session
  async uploadVideoAsset(file: File): Promise<UploadVideoAssetResponse> {
    const formData = new FormData();
    formData.append("file", file);

    try {
      return await $api<UploadVideoAssetResponse>(
        `/v2/storage/video/media/uploads/${encodeURIComponent(file.name)}`,
        {
          method: "POST",
          body: formData,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. The README and script of one variant, as text. The backend has no
  // zip yet, so the files are saved one by one
  async getScriptPackage(
    body: GetScriptPackageRequest,
  ): Promise<GetScriptPackageResponse> {
    try {
      return await $api<GetScriptPackageResponse>(
        `${BASE_URL}/scripts/package`,
        { method: "POST", body },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. One variant per call
  async assembleVideo(
    body: AssembleVideoRequest,
  ): Promise<AssembleVideoResponse> {
    try {
      return await $api<AssembleVideoResponse>(`${BASE_URL}/assemble`, {
        method: "POST",
        body,
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. A fresh link to a stored file, since the ones the generations return
  // expire within the hour. The route checks that the account in its path is
  // the one in the key (`<kind>/<account_id>/...`), so it's read from there
  async getDownloadUrl(storageKey: string): Promise<VideoAssetDownloadUrl> {
    const accountId = storageKey.split("/")[1];

    if (!accountId) {
      throw new Error(`Invalid storage key: ${storageKey}`);
    }

    try {
      const response = await $api<{ ok: boolean; data: VideoAssetDownloadUrl }>(
        `/v2/storage/video/${encodeURIComponent(accountId)}/download-url`,
        {
          method: "POST",
          body: { key: storageKey },
        },
      );

      return response.data;
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. Polled while a generation runs. `null` while the job isn't there:
  // before its first shot starts, after it expires, or when the job state
  // lives in the memory of another backend worker. Sinergia passes the 404
  // as a `FURY001` with the status in its text
  async getJobProgress(jobId: string): Promise<VideoJobProgress | null> {
    try {
      return await $api<VideoJobProgress>(
        `${BASE_URL}/jobs/${encodeURIComponent(jobId)}`,
        { method: "GET" },
      );
    } catch (error: any) {
      if (/HTTP 404/.test(error?.message?.text ?? "")) return null;

      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. An ad with no saved progress answers `exists: false`, not a 404
  async getDraft(adId: number): Promise<VideoDraft> {
    try {
      return await $api<VideoDraft>(`${BASE_URL}/draft/${adId}`, {
        method: "GET",
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. A storage failure doesn't fail the request, so check the response
  // for what was actually saved
  async saveDraft(body: SaveVideoDraftRequest): Promise<VideoDraft> {
    try {
      return await $api<VideoDraft>(`${BASE_URL}/draft`, {
        method: "POST",
        body,
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. A voice that doesn't exist answers `found: false`, not a 404
  async getVoice(voiceId: string): Promise<GetVideoVoiceResponse> {
    try {
      return await $api<GetVideoVoiceResponse>(
        `${BASE_URL}/voices/${encodeURIComponent(voiceId)}`,
        { method: "GET" },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. Can only be set, never cleared
  async markVariantReviewed(
    body: MarkVideoVariantReviewedRequest,
  ): Promise<MarkVideoVariantReviewedResponse> {
    try {
      return await $api<MarkVideoVariantReviewedResponse>(
        `${BASE_URL}/variant/reviewed`,
        { method: "POST", body },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Free. A POST because the ids are a list
  async getVariantReviewStatus(
    body: GetVideoVariantReviewStatusRequest,
  ): Promise<GetVideoVariantReviewStatusResponse> {
    try {
      return await $api<GetVideoVariantReviewStatusResponse>(
        `${BASE_URL}/variant/review-status`,
        { method: "POST", body },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async getVoices(
    query: GetVideoVoicesRequest,
  ): Promise<GetVideoVoicesResponse> {
    try {
      return await $api<GetVideoVoicesResponse>(`${BASE_URL}/voices`, {
        method: "GET",
        query,
      });
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  async generateVoiceover(
    body: GenerateVideoVoiceoverRequest,
  ): Promise<GenerateVideoVoiceoverResponse> {
    try {
      return await $api<GenerateVideoVoiceoverResponse>(
        `${BASE_URL}/voiceover`,
        {
          method: "POST",
          body,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Billed. Generates one shot's clip again, replacing the one in the draft
  async editSegmentShot(
    body: EditVideoSegmentShotRequest,
  ): Promise<EditVideoSegmentShotResponse> {
    try {
      return await $api<EditVideoSegmentShotResponse>(
        `${BASE_URL}/segments/edit-shot`,
        {
          method: "POST",
          body,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },

  // Billed per character of the line. Generates one shot's audio again,
  // replacing the one in the draft. Scripts Only
  async regenerateVoiceoverShot(
    body: RegenerateVideoVoiceoverShotRequest,
  ): Promise<RegenerateVideoVoiceoverShotResponse> {
    try {
      return await $api<RegenerateVideoVoiceoverShotResponse>(
        `${BASE_URL}/voiceover/regenerate-shot`,
        {
          method: "POST",
          body,
        },
      );
    } catch (error: any) {
      handleCommonErrors(error);
      throw error;
    }
  },
};
