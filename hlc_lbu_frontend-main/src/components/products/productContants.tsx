import { CategoryRefinerStyles } from "../forms/category-refiner/categoryRefinerTypes";

export const productRefinerStyles: CategoryRefinerStyles = {
  // Mandatory
  value_proposition: { icon: "tabler-crown", variant: "primary" },
  competitive_advantage: { icon: "tabler-trophy", variant: "info" },
  features: { icon: "tabler-puzzle", variant: "gray" },
  benefits: { icon: "tabler-thumb-up", variant: "success" },
  keywords: { icon: "tabler-key", variant: "primary" },

  // Optional
  faqs: { icon: "tabler-question-mark", variant: "primary" },
  warranties: { icon: "tabler-award", variant: "success" },
  promotions: { icon: "tabler-gift", variant: "error" },
  pricing: { icon: "tabler-currency-dollar", variant: "info" },
};
