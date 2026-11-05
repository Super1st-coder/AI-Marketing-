<script setup lang="ts">
import VideoApi, {
  type VideoScriptVariant,
  type VideoVariantsEstimate,
} from "@/services/funnel-flow/paid-social/VideoApi";

const props = defineProps<{
  variants: VideoScriptVariant[];
  /** The video model, as /segments will use it. */
  model?: string | null;
}>();

const emit = defineEmits<{
  confirm: [variantIds: string[]];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t, te } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();

const selected = ref<Record<string, boolean>>({});

// What each variant's video really costs: the rendered seconds of its shots, priced as
// /segments charges them. `undefined` while loading or unpriced: shown as "—", never a guess
const estimate = ref<VideoVariantsEstimate>();
const isPricing = ref(true);

async function loadEstimate() {
  isPricing.value = true;
  try {
    // This window only opens in Full Video, where each variant's cost is its
    // video seconds. It sends the same model and resolution /segments sends,
    // from the ad's saved Settings: a 1080P video once showed half its price
    // here because the window and the charge read the resolution differently
    estimate.value = await VideoApi.estimateVariants(
      props.variants,
      "FULL_VIDEO",
      props.model,
      null,
      null,
      store.currentAd?.ad_id ?? null,
      store.currentAd?.draft.settings?.resolution ?? null,
    );
  } catch {
    // No price, so no generating (see `canConfirm`): the user is never charged
    // for a video they weren't shown the price of
    estimate.value = undefined;
  } finally {
    isPricing.value = false;
  }
}
onMounted(loadEstimate);

function variantCost(variantId: string) {
  const cost = estimate.value?.variants.find(
    (item) => item.variant_id === variantId,
  )?.video;
  return cost?.priced ? cost.lucas : undefined;
}

const rows = computed(() =>
  props.variants.map((variant) => {
    const axisKey = `funnel-flow.paid-social.ads.video.scripts.axes.${variant.axis}`;

    return {
      variant,
      axisLabel: te(axisKey) ? t(axisKey) : variant.axis,
      inputId: `ads-assembly-video-storyboard-generate-${variant.variant_id}`,
      cost: variantCost(variant.variant_id),
    };
  }),
);

const selectedIds = computed(() =>
  props.variants
    .map((variant) => variant.variant_id)
    .filter((variantId) => selected.value[variantId]),
);

// Unknown when any selected variant has no price yet
const totalCost = computed(() => {
  const costs = selectedIds.value.map(variantCost);
  if (costs.some((cost) => cost === undefined)) return undefined;
  return costs.reduce<number>((total, cost) => total + (cost ?? 0), 0);
});

// The company's real Luca Credits balance. While it's unknown (not loaded or the credits service
// is down) nothing is blocked here: the backend refuses the generation if credits run short
const { balance: creditsBalance, ensureLoaded: ensureCreditsLoaded } =
  useVideoCredits();
onMounted(ensureCreditsLoaded);
const availableBalance = computed(() => creditsBalance.value?.available);

// A selected variant without a price ("—") blocks generating: the user must see what they
// will be charged first (Durval, 2026-10-29). Shown as "—" when the server can't tell the
// resolution, or when the price request failed. An unknown balance still doesn't block: the
// price is shown, and the backend refuses the generation if credits run short
const isPriceUnavailable = computed(
  () =>
    !isPricing.value &&
    selectedIds.value.length > 0 &&
    totalCost.value === undefined,
);

const canConfirm = computed(
  () =>
    selectedIds.value.length > 0 &&
    totalCost.value !== undefined &&
    (availableBalance.value === undefined ||
      totalCost.value <= availableBalance.value),
);

function formatCost(value: number | undefined) {
  if (value === undefined) return "—";
  return t("funnel-flow.paid-social.ads.video.storyboard.generate-modal.cost", {
    cost: value.toFixed(2),
  });
}

// ModalGeneric closes itself after emitting `confirm`
function handleConfirm() {
  emit("confirm", selectedIds.value);
}
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    :maxWidth="650"
    :continueButtonProps="{ disabled: !canConfirm }"
    @confirm="handleConfirm"
  >
    <template #title>
      {{
        $t("funnel-flow.paid-social.ads.video.storyboard.generate-modal.title")
      }}
    </template>

    <template #description>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.storyboard.generate-modal.description",
        )
      }}
    </template>

    <ul class="tw:flex tw:flex-col tw:gap-4">
      <li v-for="row in rows" :key="row.variant.variant_id">
        <CardBase
          class="tw:flex tw:items-center tw:justify-between tw:gap-4 tw:p-4"
          borderRadius="md"
          :shadow="false"
        >
          <label :for="row.inputId" class="tw:min-w-0 tw:cursor-pointer">
            <span class="tw:mb-1 tw:block tw:truncate tw:font-bold">
              {{ row.variant.title }} · {{ row.axisLabel }}
            </span>

            <span class="tw:block tw:text-sm tw:text-secondary-text">
              {{ formatCost(row.cost) }}
            </span>
          </label>

          <FieldBaseCheckbox
            v-model="selected[row.variant.variant_id]"
            :name="row.inputId"
            variant="switch"
            size="lg"
          />
        </CardBase>
      </li>
    </ul>

    <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:md:grid-cols-2">
      <AdsAssemblyVideoCreditStatCard
        icon="tabler:atom-2"
        iconVariant="primary"
        :label="
          $t(
            'funnel-flow.paid-social.ads.video.settings.credit-estimation.estimated-total-cost',
          )
        "
        :value="formatCost(totalCost)"
      />

      <AdsAssemblyVideoCreditStatCard
        icon="tabler:wallet"
        iconVariant="success"
        :label="
          $t(
            'funnel-flow.paid-social.ads.video.settings.credit-estimation.available-balance',
          )
        "
        :value="
          availableBalance === undefined ? '—' : formatCost(availableBalance)
        "
      />
    </div>

    <p
      v-if="isPriceUnavailable"
      class="tw:text-sm tw:text-secondary-text"
      role="alert"
    >
      {{
        $t(
          "funnel-flow.paid-social.ads.video.storyboard.generate-modal.price-unavailable",
        )
      }}
      <button
        type="button"
        class="tw:font-bold tw:underline"
        @click="loadEstimate"
      >
        {{
          $t(
            "funnel-flow.paid-social.ads.video.storyboard.generate-modal.retry-price",
          )
        }}
      </button>
    </p>

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>

    <template #continue>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.storyboard.generate-modal.confirm",
        )
      }}
    </template>
  </ModalGeneric>
</template>
