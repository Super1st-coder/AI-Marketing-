<script setup lang="ts">
/**
 * Low-balance warning for the video flow: at 75% of the company's credits used (warning), 90%
 * (critical) and when nothing is left, with an "Add credits" button. Hidden while the
 * balance is fine or unknown.
 */
const { balance, level, usagePct, ensureLoaded } = useVideoCredits();
const { locale } = useI18n();

onMounted(ensureLoaded);

const alertType = computed(() => (level.value === "low" ? "warning" : "error"));

const isAddCreditsOpen = ref(false);
</script>

<template>
  <Alert
    v-if="balance && level !== 'ok'"
    :type="alertType"
    data-testid="video-credit-alert"
  >
    <template #title>
      {{ $t(`funnel-flow.paid-social.ads.video.credits.alert.${level}.title`) }}
    </template>

    {{
      $t(`funnel-flow.paid-social.ads.video.credits.alert.${level}.text`, {
        pct: Math.round(usagePct),
        available: formatNumberValue(balance.available, locale),
      })
    }}

    <template #actions>
      <Button
        size="sm"
        leftIcon="tabler:shopping-cart"
        @click="isAddCreditsOpen = true"
      >
        {{ $t("funnel-flow.paid-social.ads.video.credits.add-credits.button") }}
      </Button>

      <AdsAssemblyVideoAddCreditsModal v-model="isAddCreditsOpen" />
    </template>
  </Alert>
</template>
