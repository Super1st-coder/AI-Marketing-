import { IconCardVariant } from "@/components/cards/IconCard.vue";
import { MetricGroup } from "@/services/UtilsApi";
import { RouteLocationRaw } from "vue-router";

export const metricGroupColumnStyles: Record<
  MetricGroup,
  { variant: IconCardVariant; icon: string }
> = {
  Goals: { variant: "info", icon: "tabler-flag" },
  Resources: { variant: "primary", icon: "tabler-flag" },
  Marketing: { variant: "success", icon: "tabler-chart-area-line" },
};

export type ChannelGroupStyle = {
  icon: string;
  color: IconCardVariant;
  topChannels: string[];
  availableInFunnelFlow: boolean;
  route?: RouteLocationRaw;
};

export const groupChannelStyles: Record<string, ChannelGroupStyle> = {
  default: {
    icon: "tabler-question-mark",
    color: "none",
    topChannels: [],
    availableInFunnelFlow: false,
    route: undefined,
  },
  [PAID_SOCIAL_CHANNEL_GROUP_NAME]: {
    icon: "tabler-speakerphone",
    color: "success" as const,
    topChannels: [
      "facebook-ads",
      "instagram-ads",
      "linkedin-ads",
      "twitter-ads",
      "tiktok-ads",
    ],
    availableInFunnelFlow: true,
    route: { name: "FunnelPaidSocial" },
  },
  "Paid Search": {
    icon: "tabler-mouse",
    color: "primary" as const,
    topChannels: ["google-ads", "bing-ads", "amazon-advertising"],
    availableInFunnelFlow: false,
    route: { name: "FunnelPaidSearch" },
  },
  Display: {
    icon: "tabler-device-desktop",
    color: "info" as const,
    topChannels: ["google-display-network", "programmatic", "mobile-apps"],
    availableInFunnelFlow: false,
    route: undefined,
  },
  "Organic Search": {
    icon: "tabler-search",
    color: "info" as const,
    topChannels: ["google", "bing", "yahoo"],
    availableInFunnelFlow: false,
    route: { name: "FunnelOrganicSearch" },
  },
  "Organic Social": {
    icon: "tabler-world",
    color: "primary" as const,
    topChannels: ["facebook", "instagram", "tiktok", "twitter", "linkedin"],
    availableInFunnelFlow: false,
    route: undefined,
  },
  Email: {
    icon: "tabler-mail",
    color: "success" as const,
    topChannels: ["newsletters", "promotional-emails", "welcome-emails"],
    availableInFunnelFlow: false,
    route: undefined,
  },
  Referral: {
    icon: "tabler-link",
    color: "info" as const,
    topChannels: ["blogs", "news-sites", "forums"],
    availableInFunnelFlow: false,
    route: undefined,
  },
  Affiliates: {
    icon: "ic:round-people-alt",
    color: "primary" as const,
    topChannels: ["affiliate-programs", "affiliate-networks", "influencers"],
    availableInFunnelFlow: false,
    route: undefined,
  },
} as const;

export function getGroupChannelStyles(name: string) {
  return groupChannelStyles[name] ?? groupChannelStyles.default;
}
