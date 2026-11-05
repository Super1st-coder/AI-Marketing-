<script setup lang="ts">
import { VideoScriptVariant } from "@/services/funnel-flow/paid-social/VideoApi";

export interface VideoScriptVariantReviewState {
  reviewed: boolean;
  dirty: boolean;
}

const props = defineProps<{
  variants: VideoScriptVariant[];
  states: Record<string, VideoScriptVariantReviewState>;
}>();

const emit = defineEmits<{
  review: [variantId: string];
  saveChanges: [variantId: string];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t, te } = useI18n();

// A dirty variant was necessarily visited, so unsaved changes take precedence
const rows = computed(() =>
  props.variants.map((variant, index) => {
    const state = props.states[variant.variant_id];
    const axisKey = `funnel-flow.paid-social.ads.video.scripts.axes.${variant.axis}`;

    return {
      variant,
      number: index + 1,
      axisLabel: te(axisKey) ? t(axisKey) : variant.axis,
      status: state?.dirty
        ? ("dirty" as const)
        : state?.reviewed
          ? ("reviewed" as const)
          : ("unreviewed" as const),
    };
  }),
);

const pendingRows = computed(() =>
  rows.value.filter((row) => row.status !== "reviewed"),
);

const nextPendingRow = computed(() => pendingRows.value[0]);

function handleRowAction(row: (typeof rows.value)[number]) {
  isOpen.value = false;

  if (row.status === "dirty") {
    emit("saveChanges", row.variant.variant_id);
  } else {
    emit("review", row.variant.variant_id);
  }
}

// ModalGeneric closes itself after emitting `confirm`
function handleConfirm() {
  if (!nextPendingRow.value) return;

  if (nextPendingRow.value.status === "dirty") {
    emit("saveChanges", nextPendingRow.value.variant.variant_id);
  } else {
    emit("review", nextPendingRow.value.variant.variant_id);
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
      {{ $t("funnel-flow.paid-social.ads.video.scripts.review-modal.title") }}
    </template>

    <template #description>
      {{
        $t("funnel-flow.paid-social.ads.video.scripts.review-modal.description")
      }}
    </template>

    <CardBase class="tw:overflow-hidden" borderRadius="sm" :shadow="false">
      <div
        class="tw:flex tw:items-center tw:justify-between tw:gap-4 tw:border-b tw:border-gray-300 tw:px-6 tw:py-4"
      >
        <p class="tw:font-medium">
          {{
            $t(
              "funnel-flow.paid-social.ads.video.scripts.review-modal.status-title",
            )
          }}
        </p>

        <p class="tw:font-medium tw:text-primary">
          {{
            $t(
              "funnel-flow.paid-social.ads.video.scripts.review-modal.pending-count",
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
              row.status === "dirty"
                ? $t(
                    "funnel-flow.paid-social.ads.video.scripts.footer.save-changes",
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
        nextPendingRow.status === "dirty"
          ? $t(
              "funnel-flow.paid-social.ads.video.scripts.review-modal.save-changes-variant",
              { number: nextPendingRow.number },
            )
          : $t(
              "funnel-flow.paid-social.ads.video.scripts.review-modal.review-variant",
              { number: nextPendingRow.number },
            )
      }}
    </template>
  </ModalGeneric>
</template>
