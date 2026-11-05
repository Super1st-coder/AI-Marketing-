import i18n from "@/plugins/i18n";

/**
 * The label of a voice accent. The codes are the provider's, so unknown ones
 * are shown capitalized
 */
export function getVideoVoiceAccentLabel(accent: string) {
  const key = `funnel-flow.paid-social.ads.video.voiceover.accents.${accent.replaceAll(" ", "-")}`;

  return i18n.global.te(key)
    ? i18n.global.t(key)
    : accent.replace(/\b\w/g, (letter) => letter.toUpperCase());
}
