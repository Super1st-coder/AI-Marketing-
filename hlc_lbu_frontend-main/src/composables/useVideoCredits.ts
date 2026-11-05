import VideoApi, {
  type VideoCreditsBalance,
} from "@/services/funnel-flow/paid-social/VideoApi";
import {
  BillingError,
  InsufficientCreditsError,
} from "@/services/common-errors";

/**
 * Usage (% of granted credits used) at which the low-balance warning appears and then turns
 * critical. Same thresholds as the billing service's usage e-mails (75/90%).
 */
export const VIDEO_CREDITS_WARNING_PCT = 75;
export const VIDEO_CREDITS_CRITICAL_PCT = 90;

export type VideoCreditsLevel = "ok" | "low" | "critical" | "empty";

// Shared across every screen of the video flow: one wallet, one request in flight.
const balance = ref<VideoCreditsBalance | null>(null);
const isLoading = ref(false);
const loadFailed = ref(false);
let inflight: Promise<void> | null = null;
// A refresh asked for while one is in flight must not reuse it: that request may have
// started before a charge and would show the old balance (HL-2739, point 5). So one more
// read is queued to run right after, and only the newest read ever updates the balance.
let rerunAfterInflight = false;
let latestRead = 0;
let loadedAt = 0;
/** A loaded balance older than this is re-read in the background on the next screen. */
const STALE_AFTER_MS = 15_000;
/**
 * Coming back to the tab re-reads the balance unless it was read this recently. Switching tabs
 * fires both `visibilitychange` and `focus`, and this keeps that to one request.
 */
const RETURN_REFRESH_AFTER_MS = 2_000;
let returnListenerInstalled = false;

/**
 * The company's Luca Credits balance for the video flow (credit counter, low-balance alert,
 * "available balance" in the cost boxes). Call `refresh()` after anything that charges credits.
 */
export function useVideoCredits() {
  // The balance is the company's, so other tabs, other people and other modules spend from it
  // too. Each tab only re-read it after its own charges, so a second tab kept showing the old
  // number (QAS: 20,115 on screen against a real 18,743). Coming back to the tab re-reads it.
  // Once per page, and only after a first load: a page that never shows credits asks for nothing.
  if (!returnListenerInstalled && typeof document !== "undefined") {
    returnListenerInstalled = true;
    const onReturn = () => {
      if (document.visibilityState !== "visible" || !balance.value) return;
      // A read already on its way is new enough: don't queue another behind it
      if (inflight || Date.now() - loadedAt < RETURN_REFRESH_AFTER_MS) return;
      void refresh();
    };
    document.addEventListener("visibilitychange", onReturn);
    window.addEventListener("focus", onReturn);
  }

  function read(): Promise<void> {
    const readId = ++latestRead;
    isLoading.value = true;
    inflight = (async () => {
      try {
        const fresh = await VideoApi.getBalance();
        // An older read finishing late never overwrites a newer one
        if (readId === latestRead) {
          balance.value = fresh;
          loadedAt = Date.now();
          loadFailed.value = false;
        }
      } catch (error) {
        console.error("Failed to load the credits balance:", error);
        loadFailed.value = true;
      } finally {
        isLoading.value = false;
        inflight = null;
      }
      if (rerunAfterInflight) {
        rerunAfterInflight = false;
        await read();
      }
    })();
    return inflight;
  }

  function refresh(): Promise<void> {
    if (inflight) {
      rerunAfterInflight = true;
      return inflight;
    }
    return read();
  }

  /**
   * Loads the balance once; later calls reuse it, re-reading in the background when it's
   * more than a few seconds old so a screen never opens on an outdated counter.
   */
  function ensureLoaded(): Promise<void> {
    if (!balance.value) return refresh();
    if (Date.now() - loadedAt > STALE_AFTER_MS) void refresh();
    return Promise.resolve();
  }

  /** % of granted credits used (0–100). The API sends a 0–1 fraction. */
  const usagePct = computed(() =>
    Math.min(100, Math.max(0, (balance.value?.usage_pct ?? 0) * 100)),
  );

  const level = computed<VideoCreditsLevel>(() => {
    const current = balance.value;
    if (!current) return "ok";
    if (current.available <= 0) return "empty";
    if (usagePct.value >= VIDEO_CREDITS_CRITICAL_PCT) return "critical";
    if (usagePct.value >= VIDEO_CREDITS_WARNING_PCT) return "low";
    return "ok";
  });

  /** Video-generation spend as a % of the company's video limit (0–100). */
  const videoSpendPct = computed(() => {
    const current = balance.value;
    if (!current?.video_cap) return 0;
    return Math.min(100, (current.video_spend / current.video_cap) * 100);
  });

  return {
    balance: readonly(balance),
    isLoading: readonly(isLoading),
    loadFailed: readonly(loadFailed),
    level,
    usagePct,
    videoSpendPct,
    refresh,
    ensureLoaded,
  };
}

/**
 * i18n key for a Luca Credits refusal (out of credits, video limit, billing down, ...), or
 * `undefined` when the error isn't a billing refusal and the screen's own message applies.
 */
export function videoCreditsErrorKey(error: unknown): string | undefined {
  if (!(error instanceof BillingError)) return undefined;
  return `funnel-flow.paid-social.ads.video.credits.errors.${error.code}`;
}

/**
 * A Luca Credits refusal carried by an Ads Assembly job (Gate 2). Fury fails the job with its
 * billing error, e.g. `{ code: "INSUFFICIENT_CREDITS", message }`, when the company has no
 * credits left, and Sinergia passes the job result through unchanged.
 */
export function creditsRefusalFromJob(
  result: unknown,
): BillingError | undefined {
  const job = result as { status?: string; error?: unknown } | undefined;
  if (job?.status !== "FAILED") return undefined;
  const error = job.error as { code?: unknown; message?: unknown } | undefined;
  if (error?.code !== "INSUFFICIENT_CREDITS") return undefined;
  return new InsufficientCreditsError(
    typeof error.message === "string" ? error.message : undefined,
  );
}
