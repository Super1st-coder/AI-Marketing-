<script setup lang="ts">
/**
 * The company's Luca Credits at a glance, for the video flow's page header: credits left, a
 * usage bar and the video-limit spend. Data: `useVideoCredits` (loaded once, shared).
 */
const { balance, loadFailed, level, usagePct, videoSpendPct, ensureLoaded } =
  useVideoCredits();
const { locale } = useI18n();

onMounted(ensureLoaded);

const availableLabel = computed(() =>
  balance.value
    ? formatNumberValue(balance.value.available, locale.value)
    : "—",
);

const toneClass = computed(() =>
  level.value === "ok"
    ? "tw:text-primary-text"
    : level.value === "low"
      ? "tw:text-warning"
      : "tw:text-error",
);

const barClass = computed(() =>
  level.value === "ok"
    ? "tw:bg-success"
    : level.value === "low"
      ? "tw:bg-warning"
      : "tw:bg-error",
);

/** LUCA → whole dollars (100 LUCA = $1), for the video-limit line. */
function dollars(lucas: number) {
  return formatNumberValue(Math.round(lucas / 100), locale.value);
}
</script>

<template>
  <CardBase
    borderRadius="md"
    class="tw:flex tw:min-w-56 tw:items-center tw:gap-3 tw:px-4 tw:py-3"
    data-testid="video-credit-counter"
  >
    <Icon icon="custom:hi-luca" class="tw:shrink-0 tw:text-2xl" />

    <div class="tw:flex tw:min-w-0 tw:flex-1 tw:flex-col tw:gap-1">
      <p class="tw:text-xs tw:text-secondary-text">
        {{ $t("funnel-flow.paid-social.ads.video.credits.counter.label") }}
      </p>

      <p
        v-if="loadFailed && !balance"
        class="tw:text-sm tw:text-secondary-text"
      >
        {{
          $t("funnel-flow.paid-social.ads.video.credits.counter.unavailable")
        }}
      </p>

      <template v-else>
        <p class="tw:text-base tw:font-bold" :class="toneClass">
          {{
            $t("funnel-flow.paid-social.ads.video.credits.counter.available", {
              amount: availableLabel,
            })
          }}
        </p>

        <div
          class="tw:h-1.5 tw:w-full tw:overflow-hidden tw:rounded-full tw:bg-gray-200"
          role="progressbar"
          :aria-valuenow="Math.round(usagePct)"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="
            $t('funnel-flow.paid-social.ads.video.credits.counter.used-pct', {
              pct: Math.round(usagePct),
            })
          "
        >
          <div
            class="tw:h-full tw:rounded-full tw:transition-all"
            :class="barClass"
            :style="{ width: `${usagePct}%` }"
          />
        </div>

        <p v-if="balance?.video_cap" class="tw:text-xs tw:text-secondary-text">
          {{
            $t(
              "funnel-flow.paid-social.ads.video.credits.counter.video-limit",
              {
                spent: dollars(balance.video_spend),
                cap: dollars(balance.video_cap),
                pct: Math.round(videoSpendPct),
              },
            )
          }}
        </p>
      </template>
    </div>
  </CardBase>
</template>
