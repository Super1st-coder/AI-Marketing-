<script setup lang="ts">
import { VideoScriptVariant } from "@/services/funnel-flow/paid-social/VideoApi";

const props = defineProps<{
  variants: VideoScriptVariant[];
  /**
   * Whether each variant (by `variant_id`) has its audio generated for every
   * shot. One with a failed shot can generate it again from here.
   */
  reviewed: Record<string, boolean>;
  /** The variant whose tab is open. Its audio can be generated from here. */
  currentVariantId?: string;
  /**
   * Whether the current variant can generate its audio, e.g. it has a voice.
   * When it can't, its row asks to select a voice and only closes the modal.
   */
  canGenerate: boolean;
}>();

const emit = defineEmits<{
  review: [variantId: string];
  generateAudio: [variantId: string];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t, te } = useI18n();

type Row = {
  variant: VideoScriptVariant;
  number: number;
  axisLabel: string;
  status: "reviewed" | "generate" | "selectVoice" | "review";
};

function getStatus(variantId: string): Row["status"] {
  if (props.reviewed[variantId]) return "reviewed";
  if (variantId !== props.currentVariantId) return "review";

  return props.canGenerate ? "generate" : "selectVoice";
}

const rows = computed<Row[]>(() =>
  props.variants.map((variant, index) => {
    const axisKey = `funnel-flow.paid-social.ads.video.scripts.axes.${variant.axis}`;

    return {
      variant,
      number: index + 1,
      axisLabel: te(axisKey) ? t(axisKey) : variant.axis,
      status: getStatus(variant.variant_id),
    };
  }),
);

const pendingRows = computed(() =>
  rows.value.filter((row) => row.status !== "reviewed"),
);

// The current variant goes first, since its tab is already open
const nextPendingRow = computed(
  () =>
    pendingRows.value.find(
      (row) => row.variant.variant_id === props.currentVariantId,
    ) ?? pendingRows.value[0],
);

// Selecting a voice happens in the open tab, so closing the modal is enough
function runRowAction(row: Row) {
  if (row.status === "generate") {
    emit("generateAudio", row.variant.variant_id);
  } else if (row.status === "review") {
    emit("review", row.variant.variant_id);
  }
}

function handleRowAction(row: Row) {
  isOpen.value = false;
  runRowAction(row);
}

// ModalGeneric closes itself after emitting `confirm`
function handleConfirm() {
  if (nextPendingRow.value) {
    runRowAction(nextPendingRow.value);
  }
}
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    :maxWidth="540"
    :continueButtonProps="{ icon: 'tabler:arrow-right' }"
    @confirm="handleConfirm"
  >
    <template #title>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.voiceover.review-modal.title",
          pendingRows.length,
        )
      }}
    </template>

    <template #description>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.voiceover.review-modal.description",
        )
      }}
    </template>

    <CardBase class="tw:overflow-hidden" borderRadius="sm" :shadow="false">
      <div
        class="tw:flex tw:items-center tw:justify-between tw:gap-4 tw:border-b tw:border-gray-300 tw:px-6 tw:py-4"
      >
        <p class="tw:font-medium">
          {{
            $t(
              "funnel-flow.paid-social.ads.video.voiceover.review-modal.status-title",
            )
          }}
        </p>

        <p class="tw:font-medium tw:text-primary">
          {{
            $t(
              "funnel-flow.paid-social.ads.video.voiceover.review-modal.pending-count",
              { count: pendingRows.length },
            )
          }}
        </p>
      </div>

      <ul class="tw:divide-y tw:divide-gray-300">
        <li
          v-for="row in rows"
          :key="row.variant.variant_id"
          class="tw:flex tw:items-center tw:justify-between tw:gap-4 tw:px-6 tw:py-4"
        >
          <div class="tw:min-w-0">
            <p class="tw:truncate tw:text-sm tw:font-semibold">
              {{ row.variant.title }} · {{ row.axisLabel }}
            </p>

            <p class="tw:flex tw:text-xs tw:text-secondary-text">
              "<span class="tw:truncate">{{ row.variant.hook }}</span
              >"
            </p>
          </div>

          <Chip
            v-if="row.status === 'reviewed'"
            class="tw:shrink-0"
            color="success"
            variant="label"
            size="md"
            leftIcon="tabler:check"
            uppercase
          >
            {{
              $t(
                "funnel-flow.paid-social.ads.video.scripts.review-modal.reviewed",
              )
            }}
          </Chip>

          <Button
            v-else
            class="tw:shrink-0"
            variant="text"
            size="sm"
            icon="tabler:arrow-up-right"
            type="button"
            @click="handleRowAction(row)"
          >
            {{
              row.status === "generate"
                ? $t(
                    "funnel-flow.paid-social.ads.video.voiceover.review-modal.generate-audio",
                  )
                : row.status === "selectVoice"
                  ? $t(
                      "funnel-flow.paid-social.ads.video.voiceover.review-modal.select-voice",
                    )
                  : $t("global.review")
            }}
          </Button>
        </li>
      </ul>
    </CardBase>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>

    <template v-if="nextPendingRow" #continue>
      {{
        nextPendingRow.status === "generate"
          ? $t(
              "funnel-flow.paid-social.ads.video.voiceover.review-modal.generate-audio-variant",
              { number: nextPendingRow.number },
            )
          : nextPendingRow.status === "selectVoice"
            ? $t(
                "funnel-flow.paid-social.ads.video.voiceover.review-modal.select-voice-variant",
                { number: nextPendingRow.number },
              )
            : $t(
                "funnel-flow.paid-social.ads.video.voiceover.review-modal.review-variant",
                { number: nextPendingRow.number },
              )
      }}
    </template>
  </ModalGeneric>
</template>
