import natural from "@/assets/image-studio/effects/natural.jpg";
import flash from "@/assets/image-studio/effects/flash.jpg";
import studio from "@/assets/image-studio/effects/studio.jpg";
import dramatic from "@/assets/image-studio/effects/dramatic.jpg";
import golden_hour from "@/assets/image-studio/effects/golden_hour.jpg";
import volumetric from "@/assets/image-studio/effects/volumetric.jpg";
import chiaroscuro from "@/assets/image-studio/effects/chiaroscuro.jpg";
import back_light from "@/assets/image-studio/effects/back_light.jpg";
import hardlight from "@/assets/image-studio/effects/hardlight.jpg";
import indoor_light from "@/assets/image-studio/effects/indoor_light.jpg";
import sepia from "@/assets/image-studio/effects/sepia.jpg";
import black_white from "@/assets/image-studio/effects/black_white.jpg";
import visualStyleNatural from "@/assets/image-studio/visual-styles/natural.jpg";
import visualStyleEditorial from "@/assets/image-studio/visual-styles/editorial.jpg";
import visualStyleStudioShot from "@/assets/image-studio/visual-styles/studio_shot.jpg";
import visualStyleDisposableCamera from "@/assets/image-studio/visual-styles/disposable_camera.jpg";
import visualStyleFashionInfluencer from "@/assets/image-studio/visual-styles/fashion_influencer.jpg";
import visualStyleStreetwearCatalog from "@/assets/image-studio/visual-styles/streetwear_catalog.jpg";
import visualStyleCharacter3d from "@/assets/image-studio/visual-styles/character_3d.jpg";
import visualStyleIllustration from "@/assets/image-studio/visual-styles/illustration.jpg";
import visualStyleCraftMotion from "@/assets/image-studio/visual-styles/craft_motion.jpg";
import visualStylePlasticinePeople from "@/assets/image-studio/visual-styles/plasticine_people.jpg";
import visualStyleCartoonFun from "@/assets/image-studio/visual-styles/cartoon_fun.jpg";
import visualStyleLooseLinesDesign from "@/assets/image-studio/visual-styles/loose_lines_design.jpg";
import visualStyleBoldFlat from "@/assets/image-studio/visual-styles/bold_flat.jpg";
import visualStyleMinimalCharacters3d from "@/assets/image-studio/visual-styles/minimal_characters_3d.jpg";
import visualStyleVinyl3dCharacter from "@/assets/image-studio/visual-styles/vinyl_3d_character.jpg";
import visualStyleFaceless3dCharacters from "@/assets/image-studio/visual-styles/faceless_3d_characters.jpg";

export const IMAGE_STUDIO_MAX_REFERENCE_IMAGES = 5;
export const IMAGE_STUDIO_VISUAL_STYLE_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

export const IMAGE_STUDIO_EXPAND_ZOOM_DIRECTIONAL: {
  value: ImageStudioExpandZoom;
  icon: string;
  labelKey: string;
}[] = [
  { value: "TOP", icon: "tabler:arrow-up", labelKey: "top" },
  { value: "BOTTOM", icon: "tabler:arrow-down", labelKey: "bottom" },
  { value: "LEFT", icon: "tabler:arrow-left", labelKey: "left" },
  { value: "RIGHT", icon: "tabler:arrow-right", labelKey: "right" },
];

export const IMAGE_STUDIO_EXPAND_ZOOM_UNIFORM: {
  value: ImageStudioExpandZoom;
  icon: string;
  labelKey: string;
}[] = [
  { value: "ZOOM_2X", icon: "tabler:arrows-diagonal", labelKey: "2x" },
  { value: "ZOOM_1_5X", icon: "tabler:arrows-diagonal", labelKey: "1-5x" },
  { value: "ZOOM_1_25X", icon: "tabler:arrows-diagonal", labelKey: "1-25x" },
];

/** When enabled, hides creating custom visual styles in Image Studio. */
export const IMAGE_STUDIO_DISABLE_CUSTOM_VISUAL_STYLES = true;

export const IMAGE_STUDIO_PHOTOGRAPHIC_EFFECTS: ImageStudioPhotographicEffect[] =
  [
    {
      name: "natural",
      image_url: natural,
    },
    {
      name: "flash",
      image_url: flash,
    },
    {
      name: "studio",
      image_url: studio,
    },
    {
      name: "dramatic",
      image_url: dramatic,
    },
    {
      name: "golden_hour",
      image_url: golden_hour,
    },
    {
      name: "volumetric",
      image_url: volumetric,
    },
    {
      name: "chiaroscuro",
      image_url: chiaroscuro,
    },
    {
      name: "back_light",
      image_url: back_light,
    },
    {
      name: "hardlight",
      image_url: hardlight,
    },
    {
      name: "indoor_light",
      image_url: indoor_light,
    },
    {
      name: "sepia",
      image_url: sepia,
    },
    {
      name: "black_white",
      image_url: black_white,
    },
  ];

export const IMAGE_STUDIO_VISUAL_STYLES: ImageStudioVisualStyle[] = [
  {
    name: "natural",
    image_url: visualStyleNatural,
  },
  {
    name: "editorial",
    image_url: visualStyleEditorial,
  },
  {
    name: "studio_shot",
    image_url: visualStyleStudioShot,
  },
  {
    name: "disposable_camera",
    image_url: visualStyleDisposableCamera,
  },
  {
    name: "fashion_influencer",
    image_url: visualStyleFashionInfluencer,
  },
  {
    name: "streetwear_catalog",
    image_url: visualStyleStreetwearCatalog,
  },
  {
    name: "character_3d",
    image_url: visualStyleCharacter3d,
  },
  {
    name: "illustration",
    image_url: visualStyleIllustration,
  },
  {
    name: "craft_motion",
    image_url: visualStyleCraftMotion,
  },
  {
    name: "plasticine_people",
    image_url: visualStylePlasticinePeople,
  },
  {
    name: "cartoon_fun",
    image_url: visualStyleCartoonFun,
  },
  {
    name: "loose_lines_design",
    image_url: visualStyleLooseLinesDesign,
  },
  {
    name: "bold_flat",
    image_url: visualStyleBoldFlat,
  },
  {
    name: "minimal_characters_3d",
    image_url: visualStyleMinimalCharacters3d,
  },
  {
    name: "vinyl_3d_character",
    image_url: visualStyleVinyl3dCharacter,
  },
  {
    name: "faceless_3d_characters",
    image_url: visualStyleFaceless3dCharacters,
  },
];
