<script setup lang="ts">
/**
 * The company's Luca Credits in the top bar, so the balance is visible on every page (Marco,
 * 2026-10-09). Compact on purpose: just the amount; the full counter opens on click.
 *
 * Hidden until the balance loads, and stays hidden when it can't: environments without the
 * credits service show nothing rather than a broken chip.
 *
 * Luca Credits isn't released in production yet, so it only shows where the video flow is on
 * (DEV, QAS). Production doesn't even ask for the balance: it stays hidden there even once
 * the credits service runs in production (e.g. for the brand limit).
 */
const authStore = useAuthStore();
const { balance, level, ensureLoaded } = useVideoCredits();
const { locale } = useI18n();
const showsCredits = IS_VIDEO_GENERATION_ENABLED_BY_DEFAULT;

onMounted(() => {
  if (showsCredits && authStore.userEmail) ensureLoaded();
});

/** "10,855", or "1.2M" once the number would crowd the header. */
const amountLabel = computed(() => {
  const available = balance.value?.available ?? 0;
  if (available < 100_000) return formatNumberValue(available, locale.value);
  return new Intl.NumberFormat(locale.value, {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(available);
});

const color = computed(() =>
  level.value === "ok"
    ? "primary"
    : level.value === "low"
      ? "warning"
      : "error",
);
</script>

<template>
  <ButtonDropdown
    v-if="showsCredits && authStore.userEmail && balance"
    leftIcon="custom:hi-luca"
    variant="label"
    :color="color"
    size="sm"
    type="button"
    placement="bottom-end"
    noContentPadding
    :aria-label="$t('funnel-flow.paid-social.ads.video.credits.counter.label')"
    data-testid="top-nav-credits-chip"
  >
    {{
      $t("funnel-flow.paid-social.ads.video.credits.chip", {
        amount: amountLabel,
      })
    }}

    <template #options>
      <AdsAssemblyVideoCreditCounter class="tw:border-0" />
    </template>
  </ButtonDropdown>
</template>
