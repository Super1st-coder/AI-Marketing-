import posthog from "posthog-js";

export function usePostHog() {
  if (typeof window !== "undefined" && !posthog.__loaded) {
    const key = import.meta.env.VITE_POSTHOG_KEY;
    if (!key) {
      return { posthog };
    }

    posthog.init(key, {
      api_host: "https://us.i.posthog.com",
      person_profiles: "identified_only",
    });
  }

  return { posthog };
}
