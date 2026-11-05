<script setup lang="ts">
import { VideoScriptVariant } from "@/services/funnel-flow/paid-social/VideoApi";

const props = defineProps<{
  variants: VideoScriptVariant[];
  /** Whether each variant (by `variant_id`) has been reviewed. */
  reviewed: Record<string, boolean>;
}>();

const emit = defineEmits<{
  review: [variantId: string];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t, te } = useI18n();

const rows = computed(() =>
  props.variants.map((variant, index) => {
    const axisKey = `funnel-flow.paid-social.ads.video.scripts.axes.${variant.axis}`;

    return {
      variant,
      number: index + 1,
      axisLabel: te(axisKey) ? t(axisKey) : variant.axis,
      reviewed: Boolean(props.reviewed[variant.variant_id]),
    };
  }),
);

const pendingRows = computed(() => rows.value.filter((row) => !row.reviewed));

const nextPendingRow = computed(() => pendingRows.value[0]);

function handleRowReview(variantId: string) {
  isOpen.value = false;
  emit("review", variantId);
}

// ModalGeneric closes itself after emitting `confirm`
function handleConfirm() {
  if (nextPendingRow.value) {
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
      {{
        $t(
          "funnel-flow.paid-social.ads.video.storyboard.review-modal.title",
          pendingRows.length,
        )
      }}
    </template>

    <template #description>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.storyboard.review-modal.description",
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
              "funnel-flow.paid-social.ads.video.storyboard.review-modal.status-title",
            )
          }}
        </p>

        <p class="tw:font-medium tw:text-primary">
          {{
            $t(
              "funnel-flow.paid-social.ads.video.storyboard.review-modal.pending-count",
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
            v-if="row.reviewed"
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
            @click="handleRowReview(row.variant.variant_id)"
          >
            {{ $t("global.review") }}
          </Button>
        </li>
      </ul>
    </CardBase>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>

    <template v-if="nextPendingRow" #continue>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.storyboard.review-modal.review-variant",
          { number: nextPendingRow.number },
        )
      }}
    </template>
  </ModalGeneric>
</template>
