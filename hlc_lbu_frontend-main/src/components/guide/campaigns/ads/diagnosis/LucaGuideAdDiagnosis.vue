<script setup lang="ts">
import type {
  LucaGuideAd,
  LucaGuideAdDiagnosisSlot,
} from "@/services/guide/LucaGuideAdsApi";
import type { LucaGuideCampaign } from "@/services/guide/LucaGuideCampaignsApi";

const props = withDefaults(
  defineProps<{
    ad: LucaGuideAd;
    campaign: Pick<
      LucaGuideCampaign,
      "campaign_id" | "name" | "objective_label"
    >;
    accountName: string;
    isLoading?: boolean;
    isGenerating?: boolean;
    completedSlotIndexes?: number[];
    assetType?: string;
    cards?: LucaGuideAdDiagnosisSlot[];
    window?: { startDate?: string; endDate?: string };
  }>(),
  {
    isLoading: false,
    isGenerating: false,
    completedSlotIndexes: () => [],
  },
);

const emit = defineEmits<{
  reGenerate: [];
}>();

const LOADING_CARD_COUNT = 8;

const isInsightModalOpen = ref(false);
const selectedCard = ref<LucaGuideAdDiagnosisSlot | null>(null);

const sortedCards = computed(() =>
  [...(props.cards ?? [])].sort((a, b) => a.slot_index - b.slot_index),
);

const cardCount = computed(() =>
  sortedCards.value.length > 0 ? sortedCards.value.length : LOADING_CARD_COUNT,
);

function isCardCompleted(card: LucaGuideAdDiagnosisSlot) {
  if (!props.isGenerating) {
    return true;
  }

  return props.completedSlotIndexes.includes(card.slot_index);
}

function handleViewInsight(card: LucaGuideAdDiagnosisSlot) {
  if (!isCardCompleted(card)) {
    return;
  }

  selectedCard.value = card;
  isInsightModalOpen.value = true;
}
</script>

<template>
  <div>
    <AccordionList variant="card">
      <Accordion openByDefault titleClass="tw:text-lg tw:font-bold">
        <template #title>
          {{ $t("luca-guide.ads.detail.diagnosis.section-title") }}
        </template>

        <template #description>
          {{ $t("luca-guide.ads.detail.diagnosis.section-description") }}
        </template>

        <div class="tw:flex tw:flex-col tw:gap-4">
          <div
            class="tw:flex tw:flex-wrap tw:items-center tw:justify-between tw:gap-4"
          >
            <p
              class="tw:flex tw:items-center tw:gap-1 tw:text-sm tw:text-secondary-text"
            >
              <Icon icon="tabler:palette" class="tw:text-lg" />
              <i18n-t keypath="luca-guide.ads.detail.diagnosis.meta" tag="span">
                <template #label>
                  <span class="tw:text-sm tw:font-semibold tw:uppercase">
                    {{ $t("luca-guide.ads.detail.diagnosis.meta-label") }}
                  </span>
                </template>
                <template #type>
                  {{ assetType || "—" }}
                </template>
                <template #count>
                  {{ cardCount }}
                </template>
              </i18n-t>
            </p>

            <Button
              v-if="!isLoading && !isGenerating"
              type="button"
              size="sm"
              variant="label"
              color="primary"
              leftIcon="tabler:refresh"
              @click="emit('reGenerate')"
            >
              {{ $t("luca-guide.ads.detail.diagnosis.re-generate") }}
            </Button>
          </div>

          <div class="tw:grid tw:grid-cols-1 tw:gap-4 tw:lg:grid-cols-2">
            <template v-if="isLoading">
              <LucaGuideAdDiagnosisCard
                v-for="index in LOADING_CARD_COUNT"
                :key="index"
                isLoading
              />
            </template>

            <LucaGuideAdDiagnosisCard
              v-else
              v-for="card in sortedCards"
              :key="card.slot"
              :card="card"
              :isLoading="!isCardCompleted(card)"
              @view-insight="handleViewInsight"
            />
          </div>
        </div>
      </Accordion>
    </AccordionList>

    <LucaGuideAdInsightModal
      v-if="selectedCard && isInsightModalOpen"
      v-model="isInsightModalOpen"
      :ad="ad"
      :campaign="campaign"
      :accountName="accountName"
      :card="selectedCard"
      :window="window"
    />
  </div>
</template>
