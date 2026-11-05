<script setup lang="ts">
import type {
  LucaGuideAd,
  LucaGuideAdDataDelivery,
  LucaGuideAdDataDeliveryInboxEvidence,
  LucaGuideAdDataDeliveryInboxItem,
  LucaGuideAdDiagnosisKpi,
} from "@/services/guide/LucaGuideAdsApi";
import type { LucaGuideCampaign } from "@/services/guide/LucaGuideCampaignsApi";
import type {
  LucaGuideAdRecommendedNextMoveCardData,
  LucaGuideAdRecommendedNextMoveTone,
} from "./LucaGuideAdRecommendedNextMoveCard.vue";

const LEVER_ICONS: Record<string, string> = {
  data: "tabler:chart-bar",
  delivery: "tabler:truck-delivery",
};

// Hex values from inbox_items[].actionColor (build 246), mapped to theme tokens.
const ACTION_COLOR_TONES: Record<string, LucaGuideAdRecommendedNextMoveTone> = {
  "#f59e0b": "warning",
  "#6366f1": "info",
  "#16a34a": "success",
  "#0ea5e9": "info",
};

function getActionTone(
  actionColor: string,
): LucaGuideAdRecommendedNextMoveTone {
  return ACTION_COLOR_TONES[actionColor] ?? "warning";
}

const props = defineProps<{
  ad: LucaGuideAd;
  campaign: Pick<LucaGuideCampaign, "campaign_id" | "name" | "objective_label">;
  accountName: string;
  isLoading?: boolean;
  dataDelivery?: LucaGuideAdDataDelivery | null;
}>();

const emit = defineEmits<{
  reGenerate: [];
}>();

const { t, te } = useI18n();

const isOpen = ref(!props.isLoading);
const isInsightModalOpen = ref(false);
const selectedCard = ref<LucaGuideAdRecommendedNextMoveCardData | null>(null);

watch(
  () => props.isLoading,
  (isLoading) => {
    isOpen.value = !isLoading;
  },
);

// Empty copy from the reference app: https://guide-dev.hiluca.com/app
// (`loadDataDelivery` — low-data vs healthy when no cards fire).
const emptyMessage = computed(() => {
  const summary = props.dataDelivery?.evaluation_summary;
  const lowData =
    (summary?.insufficient_data ?? 0) + (summary?.missing_data ?? 0);
  const notFired = summary?.not_fired ?? 0;

  if (summary && lowData > notFired) {
    return t("luca-guide.ads.detail.recommended-next-move.empty-low-data");
  }

  return t("luca-guide.ads.detail.recommended-next-move.empty");
});

const cards = computed((): LucaGuideAdRecommendedNextMoveCardData[] => {
  const response = props.dataDelivery;

  if (!response?.enabled) {
    return [];
  }

  return (response.inbox_items ?? []).map(mapInboxItem);
});

function getLeverLabel(lever: string) {
  const key = `luca-guide.ads.detail.recommended-next-move.levers.${lever}`;
  return te(key) ? t(key) : lever;
}

function mapInboxEvidence(
  evidence: LucaGuideAdDataDeliveryInboxEvidence[],
): LucaGuideAdDiagnosisKpi[] {
  return evidence.map((item) => {
    const match = item.detail.match(/^(.*?)\s*\((.*)\)$/);

    return {
      label: item.cardTitle,
      value: match?.[1] ?? item.detail,
      benchmark: match?.[2] ?? null,
      status: "neutral" as const,
    };
  });
}

function mapInboxItem(
  item: LucaGuideAdDataDeliveryInboxItem,
): LucaGuideAdRecommendedNextMoveCardData {
  return {
    id: item.itemId,
    category: getLeverLabel(item.lever),
    icon: LEVER_ICONS[item.lever] ?? "tabler:bolt",
    title: anyCaseToText(item.actionType),
    description: item.interpretation,
    kpis: mapInboxEvidence(item.evidence),
    actionLabel: item.suggestedActionLabel,
    tone: getActionTone(item.actionColor),
    recommendation: item.recommendedAction,
    calibrationWarning: item.calibrationWarning,
    diagnosis: item.diagnosis,
    evidence: item.evidence.map((entry) => entry.detail).join("\n"),
    riskOfNotActing: item.riskOfNotActing,
    successCriteria: item.successCriteria,
  };
}

function handleViewInsight(card: LucaGuideAdRecommendedNextMoveCardData) {
  selectedCard.value = card;
  isInsightModalOpen.value = true;
}
</script>

<template>
  <div>
    <AccordionList variant="card">
      <Accordion
        v-model="isOpen"
        :hideChevron="isLoading"
        titleClass="tw:text-lg tw:font-bold"
      >
        <template #title>
          {{ $t("luca-guide.ads.detail.recommended-next-move.title") }}
        </template>

        <template #description>
          {{ $t("luca-guide.ads.detail.recommended-next-move.description") }}
        </template>

        <template #headerEnd>
          <CircleLoader
            v-if="isLoading"
            class="tw:shrink-0 tw:text-[30px] tw:text-primary"
          />
        </template>

        <div class="tw:flex tw:flex-col tw:gap-4">
          <div class="tw:flex tw:justify-end">
            <Button
              v-if="!isLoading"
              type="button"
              size="sm"
              variant="label"
              color="primary"
              leftIcon="tabler:refresh"
              @click="emit('reGenerate')"
            >
              {{
                $t("luca-guide.ads.detail.recommended-next-move.re-generate")
              }}
            </Button>
          </div>

          <div class="tw:grid tw:grid-cols-1 tw:gap-4 tw:lg:grid-cols-2">
            <LucaGuideAdRecommendedNextMoveCard
              v-for="card in cards"
              :key="card.id"
              :card="card"
              @view-insight="handleViewInsight"
            />
          </div>

          <p
            v-if="!isLoading && !cards.length"
            class="tw:text-sm tw:text-secondary-text"
          >
            {{ emptyMessage }}
          </p>
        </div>
      </Accordion>
    </AccordionList>

    <LucaGuideAdRecommendedNextMoveModal
      v-if="selectedCard && isInsightModalOpen"
      v-model="isInsightModalOpen"
      :ad="ad"
      :campaign="campaign"
      :accountName="accountName"
      :card="selectedCard"
    />
  </div>
</template>
