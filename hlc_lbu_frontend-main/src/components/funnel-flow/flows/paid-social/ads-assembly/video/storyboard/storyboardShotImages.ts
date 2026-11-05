import VideoApi, {
  VideoDraftVariant,
  VideoScriptVariant,
} from "@/services/funnel-flow/paid-social/VideoApi";

/** One version of a shot's frame. */
export type StoryboardShotImage = {
  /** Signed link that expires within the hour. */
  image_url: string;
  /** The scene the frame was generated with. */
  scene: string;
  /**
   * Permanent reference to the stored frame, to get a fresh link when
   * `image_url` has expired. Missing when the frame couldn't be stored.
   */
  storage_key?: string | null;
};

/**
 * Every version generated for a shot. The backend only returns the new frame
 * of each edit, so the history is kept here.
 */
export type StoryboardShotImages = {
  /** Oldest first, so `v1` is at index 0. */
  history: StoryboardShotImage[];
  /** Index in `history` of the frame the shot uses. */
  activeIndex: number;
};

/** Shot `index` -> its images. */
export type StoryboardVariantShotImages = Record<number, StoryboardShotImages>;

/** `variant_id` -> its shots' images. */
export type StoryboardShotImagesByVariant = Record<
  string,
  StoryboardVariantShotImages
>;

/** Seeds every shot's history with the frame saved in the draft. */
export function createStoryboardShotImages(
  variants: VideoDraftVariant[],
): StoryboardShotImagesByVariant {
  return Object.fromEntries(
    variants.map((variant) => {
      const frames = variant.frames ?? [];

      const shotImages = Object.fromEntries(
        variant.shots.map((shot) => {
          const frame = frames.find((item) => item.shot_index === shot.index);
          const images: StoryboardShotImages = {
            history: frame
              ? [
                  {
                    image_url: frame.image_url,
                    scene: shot.scene,
                    storage_key: frame.storage_key,
                  },
                ]
              : [],
            activeIndex: 0,
          };

          return [shot.index, images];
        }),
      );

      return [variant.variant_id, shotImages];
    }),
  );
}

/** The frame the shot uses, if it has one. */
export function getActiveShotImage(
  images: StoryboardShotImages | undefined,
): StoryboardShotImage | undefined {
  return images?.history[images.activeIndex];
}

/**
 * `index` of the variant's shots whose frame failed. The storyboard
 * generation succeeds even if some frames fail, and the backend only saves
 * the ones that worked, so they're the shots without a frame.
 */
export function getFailedShotIndexes(
  variant: VideoScriptVariant,
  shotImages: StoryboardVariantShotImages | undefined,
): number[] {
  return variant.shots
    .filter((shot) => !getActiveShotImage(shotImages?.[shot.index]))
    .map((shot) => shot.index);
}

/**
 * A link to the variant's anchor frame, the one its protagonist is copied
 * from, so a regenerated frame shows the same person as the other shots.
 *
 * The saved link expires within the hour and the image provider needs to
 * download it, so a fresh one is used when there's a storage key. Undefined
 * when the variant has no anchor.
 */
export async function getVariantAnchorUrl(
  variant: VideoDraftVariant | undefined,
): Promise<string | undefined> {
  if (variant?.anchor_key) {
    return (await VideoApi.getDownloadUrl(variant.anchor_key)).url;
  }

  return variant?.anchor_url;
}
