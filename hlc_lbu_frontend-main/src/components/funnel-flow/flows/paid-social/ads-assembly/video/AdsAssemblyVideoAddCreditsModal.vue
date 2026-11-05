<script setup lang="ts">
/**
 * "Add credits": where a user lands when the next step costs more than the company has
 * (Marco, 2026-10-09: block moving forward until they add money, never leave them stuck).
 *
 * Offers fixed packs ($10/$25/$50/$100, Marco 2026-10-11) and an "other amount" option.
 * A pack becomes a payment link once its Stripe Payment Link is configured
 * (VITE_CREDITS_TOPUP_URL_<usd>, or _CUSTOM for a "customer chooses the amount" link); the
 * company is passed as client_reference_id so the payment can be credited to it. Until then the modal says how to get credits added
 * by hand, and "I've added credits" re-reads the balance so the user can carry on.
 */
const props = defineProps<{
  /** Lucas the blocked step needs beyond what's available, when known. */
  missing?: number;
}>();

const isOpen = defineModel<boolean>({ required: true });

const { balance, isLoading, refresh } = useVideoCredits();
const { t, locale } = useI18n();

/** 100 LUCA = $1 (the credits service's sale price). */
const LUCAS_PER_USD = 100;

const PACK_USD = [10, 25, 50, 100];

const TOPUP_URLS: Record<string, string | undefined> = {
  10: import.meta.env.VITE_CREDITS_TOPUP_URL_10,
  25: import.meta.env.VITE_CREDITS_TOPUP_URL_25,
  50: import.meta.env.VITE_CREDITS_TOPUP_URL_50,
  100: import.meta.env.VITE_CREDITS_TOPUP_URL_100,
  custom: import.meta.env.VITE_CREDITS_TOPUP_URL_CUSTOM,
};

/** Stripe Payment Links accept client_reference_id; it tells us which company paid. */
function paymentUrl(base: string | undefined) {
  const orgId = balance.value?.org_id;
  if (!base || !orgId) return undefined;
  const separator = base.includes("?") ? "&" : "?";
  return `${base}${separator}client_reference_id=${encodeURIComponent(orgId)}`;
}

/** The smallest pack that covers what this step is missing: the one to suggest. */
const suggestedUsd = computed(() => {
  if (!props.missing || props.missing <= 0) return undefined;
  return PACK_USD.find((usd) => usd * LUCAS_PER_USD >= props.missing!);
});

const packs = computed(() =>
  PACK_USD.map((usd) => ({
    key: String(usd),
    title: `$${usd}`,
    subtitle: t("funnel-flow.paid-social.ads.video.credits.add-credits.pack", {
      lucas: formatNumberValue(usd * LUCAS_PER_USD, locale.value),
    }),
    url: paymentUrl(TOPUP_URLS[usd]),
    suggested: usd === suggestedUsd.value,
  })).concat({
    key: "custom",
    title: t("funnel-flow.paid-social.ads.video.credits.add-credits.custom"),
    subtitle: t(
      "funnel-flow.paid-social.ads.video.credits.add-credits.custom-hint",
    ),
    url: paymentUrl(TOPUP_URLS.custom),
    // A step bigger than the biggest pack: the custom amount is the one that covers it
    suggested: Boolean(props.missing && props.missing > 0 && !suggestedUsd.value),
  }),
);

const canPayOnline = computed(() => packs.value.some((pack) => pack.url));

const availableLabel = computed(() =>
  formatNumberValue(balance.value?.available ?? 0, locale.value),
);

const missingLabel = computed(() =>
  props.missing && props.missing > 0
    ? formatNumberValue(Math.ceil(props.missing), locale.value)
    : undefined,
);

async function handleAdded() {
  await refresh();
  isOpen.value = false;
}
</script>

<template>
  <Modal v-model="isOpen" :maxWidth="680" v-slot="{ close }">
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.ads.video.credits.add-credits.title") }}

      <template #description>
        {{
          missingLabel
            ? $t(
                "funnel-flow.paid-social.ads.video.credits.add-credits.description-missing",
                {
                  missing: missingLabel,
                  available: availableLabel,
                },
              )
            : $t(
                "funnel-flow.paid-social.ads.video.credits.add-credits.description",
              )
        }}
      </template>
    </ModalHeader>

    <ModalBody class="tw:flex tw:flex-col tw:gap-4">
      <div class="tw:grid tw:grid-cols-2 tw:gap-3 tw:sm:grid-cols-5">
        <component
          :is="pack.url ? 'a' : 'div'"
          v-for="pack in packs"
          :key="pack.key"
          :href="pack.url"
          :target="pack.url ? '_blank' : undefined"
          :rel="pack.url ? 'noopener' : undefined"
          class="tw:flex tw:flex-col tw:items-center tw:gap-1 tw:rounded-xl tw:border tw:p-3 tw:text-center"
          :class="[
            pack.suggested ? 'tw:border-primary' : 'tw:border-divider',
            pack.url
              ? 'tw:cursor-pointer tw:hover:border-primary'
              : 'tw:opacity-60',
          ]"
          :data-testid="`add-credits-pack-${pack.key}`"
        >
          <span class="tw:text-lg tw:font-bold">{{ pack.title }}</span>
          <span class="tw:text-xs tw:text-secondary-text">
            {{ pack.subtitle }}
          </span>
          <span v-if="pack.suggested" class="tw:text-xs tw:text-primary">
            {{
              $t(
                "funnel-flow.paid-social.ads.video.credits.add-credits.suggested",
              )
            }}
          </span>
        </component>
      </div>

      <Alert v-if="!canPayOnline" type="info">
        {{
          $t(
            "funnel-flow.paid-social.ads.video.credits.add-credits.manual-note",
          )
        }}
      </Alert>
    </ModalBody>

    <ModalFooter>
      <Button color="secondary" variant="outlined" type="button" @click="close">
        {{ $t("global.close") }}
      </Button>

      <Button
        type="button"
        leftIcon="tabler:refresh"
        :isLoading="isLoading"
        @click="handleAdded"
      >
        {{ $t("funnel-flow.paid-social.ads.video.credits.add-credits.added") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
