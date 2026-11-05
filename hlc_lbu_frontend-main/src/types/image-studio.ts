export type ImageStudioPhotographicEffect = {
  name: string;
  image_url: string;
};

export type ImageStudioVisualStyle = {
  name: string;
  image_url?: string;
  image?: File;
};

/** Same values as the back-end. */
export type ImageStudioExpandZoom =
  "TOP" | "BOTTOM" | "LEFT" | "RIGHT" | "ZOOM_2X" | "ZOOM_1_5X" | "ZOOM_1_25X";
