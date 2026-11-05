<script setup lang="ts">
import LucaGuideOnboardingApi from "@/services/guide/LucaGuideOnboardingApi";
import type { LucaGuideTimeframe } from "@/components/guide/LucaGuideTimeFilters.vue";
import { setLucaGuideWorkspaceId } from "@/utils/guide/workspace";

const store = useLucaGuideLayoutStore();
const { goBack, goNext } = useMultiStepFormContext();
const route = useRoute();
const router = useRouter();
const brandId = useBrandId();
const { locale, t } = useI18n();

const adAccountId = ref<string | undefined>();
const isConnected = ref(false);
const isSubmitting = ref(false);
const facebookLoginError = ref(false);
const prepareError = ref<string | undefined>();
const timeframe = ref<LucaGuideTimeframe>(timeframeFromMeta());
const isEmptyWindowModalOpen = ref(false);
const isSwitchAccountModalOpen = ref(false);

/** Day presets exposed by the selector; any other saved count collapses to custom/max. */
const TIMEFRAME_DAY_PRESETS = [7, 14, 30, 90, 360];

/**
 * HLG-171: rebuild the selector state from the persisted Meta connection so the
 * saved "Historical period" rehydrates instead of always resetting to "Entire
 * period". `historical_period_days === 1095` → max; a preset day count → that
 * preset; explicit start/end → a custom window.
 */
function timeframeFromMeta(): LucaGuideTimeframe {
  const meta = store.meta;

  if (!meta) {
    return { type: "max" };
  }

  const days = meta.historical_period_days;
  const start = meta.historical_period_start;
  const end = meta.historical_period_end;

  // A custom range was saved (date_start + date_end).
  if (start && end) {
    return { type: "custom", startDate: start, days: daysSince(start) };
  }

  if (days == null || days === LUCA_GUIDE_ENTIRE_PERIOD_DAYS) {
    return { type: "max" };
  }

  if (TIMEFRAME_DAY_PRESETS.includes(days)) {
    return { type: "days", days };
  }

  return { type: "max" };
}

/** Whole days from `isoDate` (local) up to today — mirrors LucaGuideCustomDateButton. */
function daysSince(isoDate: string) {
  const start = parseLocalIsoDate(isoDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.max(
    1,
    Math.round((today.getTime() - start.getTime()) / 86_400_000),
  );
}

const connectedAdAccountId = computed(
  () => store.meta?.selected_ad_account_id ?? undefined,
);

const isAccountSwitch = computed(
  () =>
    Boolean(connectedAdAccountId.value) &&
    Boolean(adAccountId.value) &&
    adAccountId.value !== connectedAdAccountId.value,
);

const emptyWindowLabel = computed(() => {
  const next = timeframe.value;

  if (next.type === "days") {
    return {
      key: "days" as const,
      days: next.days,
      count: next.days,
    };
  }

  if (next.type === "custom") {
    return {
      key: "custom" as const,
      range: formatDateRange(
        parseIsoDate(next.startDate),
        parseIsoDate(formatLocalIsoDate(new Date())),
        locale.value,
      ),
    };
  }

  return { key: "max" as const };
});

const canContinue = computed(
  () => isConnected.value && Boolean(adAccountId.value) && !isSubmitting.value,
);

async function consumeFacebookOAuthReturn() {
  const fb = route.query.fb;
  const ws = route.query.ws;

  if (typeof ws === "string") {
    setLucaGuideWorkspaceId(brandId, ws);
    await store.initialize(brandId);
  }

  facebookLoginError.value = fb === "error";

  if (fb === undefined && ws === undefined) {
    return;
  }

  const query = { ...route.query };
  delete query.fb;
  delete query.ws;
  void router.replace({ query });
}

await consumeFacebookOAuthReturn();

// HLG-171: consumeFacebookOAuthReturn may re-initialize the store (fresh Meta
// connection), so resync the selector from the now-current persisted period.
timeframe.value = timeframeFromMeta();

async function proceedAfterPrepare() {
  await store.refreshMeta();
  await sleep(1000);
  goNext();
}

async function handleContinue() {
  if (!adAccountId.value) {
    return;
  }

  isSubmitting.value = true;
  prepareError.value = undefined;

  try {
    const next = timeframe.value;
    const dateFilter =
      next.type === "custom"
        ? {
            date_start: next.startDate,
            date_end: formatLocalIsoDate(new Date()),
          }
        : {
            days:
              next.type === "days" ? next.days : LUCA_GUIDE_ENTIRE_PERIOD_DAYS,
          };

    // The ingest is too slow to run in one HTTP request on a real account (per-ad creative
    // resolution), so kick a background job and poll it instead of holding one long request
    // open. This is what fixes the silent "Continue does nothing" block: a failure now surfaces
    // a message instead of being swallowed.
    await LucaGuideOnboardingApi.startPrepareMetaAccount(
      adAccountId.value,
      dateFilter,
    );

    const status = await pooling(
      () => LucaGuideOnboardingApi.getPrepareStatus(),
      (s) => s.state === "done" || s.state === "empty" || s.state === "failed",
      3000,
      { delayMs: 1500, timeoutMs: 5 * 60 * 1000 },
    );

    if (status.state === "failed") {
      prepareError.value = status.error ?? t("global.unexpected-error");
      return;
    }

    if (status.state === "empty") {
      isEmptyWindowModalOpen.value = true;
      return;
    }

    await proceedAfterPrepare();
  } catch (error) {
    console.error("Failed to prepare Meta account:", error);
    prepareError.value = t("global.unexpected-error");
  } finally {
    isSubmitting.value = false;
  }
}

function handleContinueClick() {
  if (isAccountSwitch.value) {
    isSwitchAccountModalOpen.value = true;
    return;
  }

  void handleContinue();
}

function revertAccountSwitch() {
  adAccountId.value = connectedAdAccountId.value;
}
</script>

<template>
  <FormStepLayout as="div" :maxWidth="1096">
    <template #stepper>
      <MultiStepFormStepper />
    </template>

    <PageTitle>
      {{ $t("luca-guide.onboarding.meta-integration.title") }}
      <template #description>
        {{ $t("luca-guide.onboarding.meta-integration.description") }}
      </template>
    </PageTitle>

    <Alert v-if="facebookLoginError" type="error">
      {{ $t("luca-guide.onboarding.meta-integration.login-error") }}
    </Alert>

    <Alert v-if="prepareError" type="error" autoScroll>
      {{ prepareError }}
    </Alert>

    <LucaGuideMetaDestinationCard
      v-model:ad-account-id="adAccountId"
      v-model:connected="isConnected"
    >
      <template #footer>
        <FieldBaseControl
          :label="$t('luca-guide.onboarding.meta-integration.timeframe-label')"
        >
          <LucaGuideTimeFilters
            v-model="timeframe"
            :options="[7, 14, 30, 90, 360, 'max', 'custom']"
            :disabled="isSubmitting"
          />
        </FieldBaseControl>
      </template>
    </LucaGuideMetaDestinationCard>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <Button
          icon="tabler-arrow-right"
          :disabled="!canContinue"
          :isLoading="isSubmitting"
          @click="handleContinueClick"
        >
          {{ $t("global.continue") }}
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>

  <!-- Switch account warning modal -->
  <ModalGeneric
    v-model="isSwitchAccountModalOpen"
    :maxWidth="650"
    :confirmFn="handleContinue"
    @cancel="revertAccountSwitch"
    @close="revertAccountSwitch"
  >
    <template #title>
      {{ $t("luca-guide.onboarding.meta-integration.account-switch.title") }}
    </template>

    <div class="tw:flex tw:flex-col tw:gap-4 tw:text-sm">
      <p class="tw:text-secondary-text">
        {{ $t("luca-guide.onboarding.meta-integration.account-switch.intro") }}
      </p>

      <ul class="tw:flex tw:flex-col tw:gap-3">
        <li class="tw:flex tw:items-start tw:gap-2">
          <Icon
            icon="tabler:trash"
            class="tw:mt-0.5 tw:shrink-0 tw:text-warning"
          />
          <span>
            {{
              $t(
                "luca-guide.onboarding.meta-integration.account-switch.consequence-analysis",
              )
            }}
          </span>
        </li>
        <li class="tw:flex tw:items-start tw:gap-2">
          <Icon
            icon="tabler:cloud-download"
            class="tw:mt-0.5 tw:shrink-0 tw:text-warning"
          />
          <span>
            {{
              $t(
                "luca-guide.onboarding.meta-integration.account-switch.consequence-data",
              )
            }}
          </span>
        </li>
        <li class="tw:flex tw:items-start tw:gap-2">
          <Icon
            icon="tabler:alert-triangle"
            class="tw:mt-0.5 tw:shrink-0 tw:text-warning"
          />
          <span>
            {{
              $t(
                "luca-guide.onboarding.meta-integration.account-switch.consequence-undo",
              )
            }}
          </span>
        </li>
      </ul>
    </div>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>

    <template #continue>
      {{ $t("luca-guide.onboarding.meta-integration.account-switch.confirm") }}
    </template>
  </ModalGeneric>

  <!-- Empty warning modal -->
  <ModalGeneric
    v-model="isEmptyWindowModalOpen"
    :maxWidth="650"
    :confirmFn="proceedAfterPrepare"
  >
    <template #title>
      {{ $t("luca-guide.onboarding.meta-integration.empty-window.title") }}
    </template>

    <Alert type="warning">
      <template v-if="emptyWindowLabel.key === 'max'">
        {{
          $t(
            "luca-guide.onboarding.meta-integration.empty-window.description-max",
          )
        }}
      </template>
      <i18n-t
        v-else
        keypath="luca-guide.onboarding.meta-integration.empty-window.description"
        tag="span"
      >
        <template #window>
          <strong>
            {{
              $t(
                `luca-guide.onboarding.meta-integration.empty-window.window.${emptyWindowLabel.key}`,
                emptyWindowLabel,
              )
            }}
          </strong>
        </template>
      </i18n-t>
    </Alert>

    <template #cancel>
      {{
        $t(
          emptyWindowLabel.key === "max"
            ? "luca-guide.onboarding.meta-integration.empty-window.cancel-max"
            : "luca-guide.onboarding.meta-integration.empty-window.cancel",
        )
      }}
    </template>

    <template #continue>
      {{ $t("global.continue") }}
    </template>
  </ModalGeneric>
</template>
