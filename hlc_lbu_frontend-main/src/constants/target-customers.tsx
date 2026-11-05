import { CategoryRefinerStyles } from "@/components/forms/category-refiner/categoryRefinerTypes";
import frontal from "@/assets/target-customers/image-variation-categories/frontal.jpg";
import side_face from "@/assets/target-customers/image-variation-categories/side_face.jpg";
import expresion from "@/assets/target-customers/image-variation-categories/expresion.jpg";
import full_body from "@/assets/target-customers/image-variation-categories/full_body.jpg";
import outfit from "@/assets/target-customers/image-variation-categories/outfit.jpg";

export const targetCustomerRefinerStyles: CategoryRefinerStyles = {
  customer_goal: { icon: "tabler-target", variant: "primary" },
  pain_points: { icon: "tabler-target", variant: "error" },
  how_they_solve_it_now: { icon: "tabler-tools", variant: "info" },
  problem_with_current_solution: {
    icon: "tabler-alert-octagon",
    variant: "error",
  },
  barriers_to_making_a_change: { icon: "tabler-wall", variant: "primary" },
  fears_and_worries: { icon: "tabler-heart-broken", variant: "gray" },
  name_and_nickname: { icon: "ic:round-people-alt", variant: "primary" },
  hometown: { icon: "tabler-building-community", variant: "info" },
  age_range: { icon: "tabler-calendar-event", variant: "success" },
  income_level_brackets: { icon: "tabler-currency-dollar", variant: "info" },
};

export const TARGET_CUSTOMER_IMAGE_VARIATION_LABELS = [
  {
    name: "frontal",
    preview_image_url: frontal,
  },
  {
    name: "side_face",
    preview_image_url: side_face,
  },
  {
    name: "expression",
    preview_image_url: expresion,
  },
  {
    name: "full_body",
    preview_image_url: full_body,
  },
  {
    name: "outfit",
    preview_image_url: outfit,
  },
];

export const TARGET_CUSTOMER_IMAGE_VARIATION_MAXIMUM_COUNT = 6;

/** When enabled, uploaded labeled variants are scanned before they are saved. */
export const TARGET_CUSTOMER_IMAGE_VARIATION_ANALYZE_ENABLED = false;

/** ModalRingLoader step interval for target-customer image generation (4 images). */
export const TARGET_CUSTOMER_IMAGE_RING_LOADER_INTERVAL_MS = 30 * SECOND_IN_MS;

export const TARGET_CUSTOMER_IMAGE_JOB_POLLING_INTERVAL_MS = 5 * SECOND_IN_MS;
export const TARGET_CUSTOMER_IMAGE_JOB_TIMEOUT_MS = 10 * MINUTE_IN_MS;
export const TARGET_CUSTOMER_IMAGE_MAIN_LIST_JOB_TIMEOUT_MS = 20 * MINUTE_IN_MS;

// TODO: replace with the real image studio help video
export const TARGET_CUSTOMER_IMAGE_STUDIO_HELP_VIDEO_URL =
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
