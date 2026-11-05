import { ProductData } from "@/services/ProductsApi";

export type ImageStudioGeneratedImage = {
  id: number;
  image_id: string;
  image_url: string;
  fetchBlob?: boolean;
  image_blob?: ImageLibraryFile | Blob;
  prompt?: string;
  has_variants?: boolean;
  selected?: boolean;
};

export type ImageStudioSelectedMainImage = Pick<
  ImageStudioGeneratedImage,
  "image_url" | "image_blob" | "prompt" | "image_id"
>;

export type ImageStudioVariationImage = {
  id: number;
  image_id: string;
  label?: string;
  image_url: string;
  image_blob?: ImageLibraryFile;
  prompt?: string;
};

export type ImageStudioDeleteFn = (
  image: ImageStudioGeneratedImage,
) => Promise<void> | void;

export type ImageStudioGenerateMode = "normal" | "edit" | "moreLikeThis";

export type ImageStudioGenerateFnOptions = {
  /** Undefined when the prompt is empty (see `allowEmptyPrompt`) */
  prompt?: string;
  variations: number;
  mode: ImageStudioGenerateMode;
  targetImage?: ImageStudioGeneratedImage;
  referenceImages?: ImageLibraryFile[];
  photographyEffect?: ImageStudioPhotographicEffect;
  visualStyle?: ImageStudioVisualStyle;
  targetProduct?: ProductData;
  /** `undefined` keeps the image as it is. */
  expandZoom?: ImageStudioExpandZoom;
};

/**
 * Throw from a `generateFn` to show `message` (already translated) in the
 * studio instead of the generic unexpected error.
 */
export class ImageStudioGenerateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

export type ImageStudioGenerateFn = (
  options: ImageStudioGenerateFnOptions,
) => Promise<ImageStudioGeneratedImage[]> | ImageStudioGeneratedImage[];
