<script setup lang="ts">
import LucaGuideCampaignsApi, {
  type LucaGuideCampaignsOverview,
} from "@/services/guide/LucaGuideCampaignsApi";
import LucaGuideOnboardingApi, {
  type LucaGuideDataSyncStatus,
} from "@/services/guide/LucaGuideOnboardingApi";
import type { LucaGuideTimeframe } from "@/components/guide/LucaGuideTimeFilters.vue";

const store = useLucaGuideLayoutStore();
const { t, locale } = useI18n();

usePageTitle(() =>
  t("routes.luca-guide-campaigns", { brand: store.brand?.name ?? "" }),
);

const timeframe = ref<LucaGuideTimeframe>({ type: "max" });
const isRefreshing = ref(false);

const overview = ref<LucaGuideCampaignsOverview>(
  await LucaGuideCampaignsApi.getOverview(LUCA_GUIDE_ENTIRE_PERIOD_DAYS),
);

// Data-sync progress (Jake): while the post-connect daily backfill is still running we tell the
// user how much history has loaded and gate the window buttons to it, so they don't (like Marco)
// read a "Last 30d" that's silently only 12 days deep. Poll while syncing; stop once ready.
const syncStatus = ref<LucaGuideDataSyncStatus | null>(null);
let syncPoll: ReturnType<typeof setInterval> | undefined;

const isSyncing = computed(() => syncStatus.value?.syncing === true);
const availableDays = computed(() => syncStatus.value?.available_days);
const syncMinDate = computed(() => syncStatus.value?.first_date ?? undefined);

// Download progress (Jake): percent + estimated time-left while the history backfill runs.
const syncPct = computed(() => {
  const p = syncStatus.value?.pct;
  return typeof p === "number"
    ? Math.max(0, Math.min(100, Math.round(p)))
    : null;
});

const syncEtaLabel = computed(() => {
  const s = syncStatus.value;
  // Only show an ETA once it's meaningful (>=5% and elapsed known) — a wrong-then-corrected
  // estimate erodes trust. time-left = elapsed × (100 − pct) / pct.
  if (!s?.started_at || s.pct == null || s.pct < 5 || s.pct >= 100) {
    return null;
  }
  const elapsed = Date.now() - new Date(s.started_at).getTime();
  if (!(elapsed > 0)) {
    return null;
  }
  const remainingMs = (elapsed * (100 - s.pct)) / s.pct;
  if (remainingMs < 5000) {
    return null;
  }
  const mins = Math.round(remainingMs / 60000);
  if (mins >= 1) {
    return t("luca-guide.sync.eta-min", { min: mins });
  }
  return t("luca-guide.sync.eta-sec", {
    sec: Math.max(5, Math.round(remainingMs / 15000) * 15),
  });
});

// The loaded date span (first → last), formatted for the coverage line so the user always sees
// exactly which dates are backing the numbers — not only while syncing (Jake).
const coverageRangeLabel = computed(() => {
  const s = syncStatus.value?.first_date;
  const e = syncStatus.value?.last_date;
  if (!s || !e) {
    return null;
  }
  return formatDateRange(
    parseLocalIsoDate(s),
    parseLocalIsoDate(e),
    locale.value,
  );
});

async function refreshSyncStatus() {
  try {
    syncStatus.value = await LucaGuideOnboardingApi.getSyncStatus();
  } catch {
    // Non-critical: if the status probe fails we simply don't gate (fail open).
    syncStatus.value = null;
  }
  if (!isSyncing.value && syncPoll) {
    clearInterval(syncPoll);
    syncPoll = undefined;
  }
}

// Manual "Refresh data": re-run the Meta download without disconnecting, then poll so the progress
// bar appears immediately (the backend flips to 'syncing' synchronously).
const isTriggeringSync = ref(false);
async function refreshData() {
  if (isTriggeringSync.value || isSyncing.value) {
    return;
  }
  isTriggeringSync.value = true;
  try {
    await LucaGuideOnboardingApi.triggerDataSync();
    await refreshSyncStatus();
    if (isSyncing.value && !syncPoll) {
      syncPoll = setInterval(refreshSyncStatus, 10_000);
    }
  } catch {
    // handled by the API layer; nothing to show inline
  } finally {
    isTriggeringSync.value = false;
  }
}

onMounted(async () => {
  await refreshSyncStatus();
  if (isSyncing.value) {
    syncPoll = setInterval(refreshSyncStatus, 15_000);
  }
});

onBeforeUnmount(() => {
  if (syncPoll) {
    clearInterval(syncPoll);
  }
});

const periodDays = computed(() => {
  if (timeframe.value.type === "days") {
    return timeframe.value.days;
  }
  if (timeframe.value.type === "custom-range") {
    const s = new Date(timeframe.value.startDate).getTime();
    const e = new Date(timeframe.value.endDate).getTime();
    return Math.max(1, Math.round((e - s) / 86_400_000) + 1);
  }
  return undefined;
});

async function loadOverview(next: LucaGuideTimeframe) {
  isRefreshing.value = true;

  try {
    if (next.type === "custom-range") {
      overview.value = await LucaGuideCampaignsApi.getOverview(
        undefined,
        next.startDate,
        next.endDate,
      );
    } else {
      const days =
        next.type === "days"
          ? next.days
          : next.type === "max"
            ? LUCA_GUIDE_ENTIRE_PERIOD_DAYS
            : undefined;
      overview.value = await LucaGuideCampaignsApi.getOverview(days);
    }
  } finally {
    isRefreshing.value = false;
  }
}
</script>

<template>
  <ContainerDashboard>
    <PageTitle>
      {{ $t("luca-guide.campaigns.title") }}
      <template #description>
        {{ $t("luca-guide.campaigns.description") }}
      </template>

      <template #after>
        <LucaGuideTimeFilters
          v-model="timeframe"
          :options="[7, 14, 30, 'max', 'custom-range']"
          :disabled="isRefreshing"
          :syncing="isSyncing"
          :availableDays="availableDays"
          :minDate="syncMinDate"
          @update:model-value="loadOverview"
        />
      </template>
    </PageTitle>

    <Alert v-if="isSyncing" type="info" class="tw:mb-2">
      <template #custom>
        <div class="tw:flex tw:w-full tw:flex-col tw:gap-2">
          <span>
            <template v-if="syncPct != null">
              {{ $t("luca-guide.sync.syncing-pct", { pct: syncPct }) }}
              <template v-if="syncEtaLabel"> · {{ syncEtaLabel }}</template>
            </template>
            <template v-else-if="availableDays">
              {{ $t("luca-guide.sync.syncing", { days: availableDays }) }}
            </template>
            <template v-else>
              {{ $t("luca-guide.sync.syncing-empty") }}
            </template>
          </span>

          <div
            v-if="syncPct != null"
            class="tw:h-1.5 tw:w-full tw:overflow-hidden tw:rounded-full tw:bg-blue-200"
            role="progressbar"
            :aria-valuenow="syncPct"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              class="tw:h-full tw:rounded-full tw:bg-blue-600 tw:transition-all tw:duration-500"
              :style="{ width: syncPct + '%' }"
            />
          </div>
        </div>
      </template>
    </Alert>

    <div
      v-else-if="availableDays"
      class="tw:mb-2 tw:flex tw:flex-wrap tw:items-center tw:gap-x-2 tw:gap-y-1 tw:text-sm tw:text-secondary-text"
    >
      <Icon icon="tabler:database" class="tw:shrink-0" />
      <span>
        {{
          coverageRangeLabel
            ? $t("luca-guide.sync.ready-range", {
                days: availableDays,
                range: coverageRangeLabel,
              })
            : $t("luca-guide.sync.ready", { days: availableDays })
        }}
      </span>
      <Button
        type="button"
        variant="text"
        size="xs"
        color="secondary"
        leftIcon="tabler:refresh"
        :shadow="false"
        :isLoading="isTriggeringSync"
        @click="refreshData"
      >
        {{ $t("luca-guide.sync.refresh") }}
      </Button>
    </div>

    <div
      class="tw:flex tw:flex-col tw:gap-6"
      :class="{ 'tw:pointer-events-none tw:opacity-60': isRefreshing }"
    >
      <LucaGuideCampaignsOverviewMetrics
        :overview="overview"
        :periodDays="periodDays"
      />

      <LucaGuideCampaignsList
        :campaigns="overview.campaigns"
        :currency="overview.currency"
      />
    </div>
  </ContainerDashboard>
</template>
