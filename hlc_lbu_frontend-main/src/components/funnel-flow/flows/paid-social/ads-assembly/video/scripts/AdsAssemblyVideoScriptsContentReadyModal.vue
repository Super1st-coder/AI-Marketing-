<script setup lang="ts">
import { VideoContentOptions } from "@/stores/funnel-flow/paid-social/FunnelPaidSocialAdsAssemblyStore";
import VideoApi, {
  type VideoProductionMode,
  type VideoScriptVariant,
  type VideoVariantsEstimate,
} from "@/services/funnel-flow/paid-social/VideoApi";

const props = defineProps<{
  /** The previous choice, if the modal was already confirmed. */
  initialOptions?: Partial<VideoContentOptions>;
  /** This ad's variants: the costs are priced from their real shots. */
  variants: VideoScriptVariant[];
  /** Decides which steps are charged: voiceover only in Scripts Only. */
  productionMode: VideoProductionMode;
  /** The video model, as the storyboard and video steps will use it. */
  model?: string | null;
}>();

const emit = defineEmits<{
  confirm: [
    options: { storyboard_enabled: boolean; voiceover_enabled: boolean },
  ];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();

const selected = ref({
  storyboard: props.initialOptions?.storyboard_enabled ?? false,
  voiceover: props.initialOptions?.voiceover_enabled ?? false,
});

// The real cost of each option, priced from this ad's variants exactly as the step is charged.
// `undefined` while loading, or when the step couldn't be priced: shown as "—", never as a guess
const estimate = ref<VideoVariantsEstimate>();
onMounted(async () => {
  try {
    estimate.value = await VideoApi.estimateVariants(
      props.variants,
      props.productionMode,
      props.model,
      null,
      null,
      store.currentAd?.ad_id ?? null,
    );
  } catch {
    // Not blocking: the backend refuses the generation if credits run short
    estimate.value = undefined;
  }
});

function stepCost(step: "storyboard" | "voiceover") {
  const cost = estimate.value?.[step];
  if (cost && !cost.applies) return 0;
  return cost?.priced ? cost.lucas : undefined;
}

const options = computed(() =>
  (
    [
      { key: "storyboard", cost: stepCost("storyboard") },
      { key: "voiceover", cost: stepCost("voiceover") },
    ] as const
  ).map((option) => ({
    ...option,
    inputId: `ads-assembly-video-content-ready-${option.key}`,
    label: t(
      `funnel-flow.paid-social.ads.video.scripts.content-ready-modal.${option.key}`,
    ),
  })),
);

// Unknown when any selected option has no price yet
const totalCost = computed(() => {
  const chosen = options.value.filter((option) => selected.value[option.key]);
  if (chosen.some((option) => option.cost === undefined)) return undefined;
  return chosen.reduce((total, option) => total + (option.cost ?? 0), 0);
});

// The company's real Luca Credits balance. While it's unknown (not loaded or the credits service
// is down) nothing is blocked here: the backend refuses the generation if credits run short
const { balance: creditsBalance, ensureLoaded: ensureCreditsLoaded } =
  useVideoCredits();
onMounted(ensureCreditsLoaded);
const availableBalance = computed(() => creditsBalance.value?.available);

const canConfirm = computed(
  () =>
    availableBalance.value === undefined ||
    totalCost.value === undefined ||
    totalCost.value <= availableBalance.value,
);

function formatCost(value: number | undefined) {
  if (value === undefined) return "—";
  return t("funnel-flow.paid-social.ads.video.storyboard.generate-modal.cost", {
    cost: value.toFixed(2),
  });
}

// ModalGeneric closes itself after emitting `confirm`
function handleConfirm() {
  emit("confirm", {
    storyboard_enabled: selected.value.storyboard,
    voiceover_enabled: selected.value.voiceover,
  });
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
        $t(
          "funnel-flow.paid-social.ads.video.scripts.content-ready-modal.title",
        )
      }}
    </template>

    <template #description>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.scripts.content-ready-modal.description",
        )
      }}
    </template>

    <ul class="tw:flex tw:flex-col tw:gap-4">
      <li v-for="option in options" :key="option.key">
        <CardBase
          class="tw:flex tw:items-center tw:justify-between tw:gap-3 tw:p-4"
          borderRadius="md"
          :shadow="false"
        >
          <label :for="option.inputId" class="tw:min-w-0 tw:cursor-pointer">
            <span class="tw:mb-1 tw:block tw:truncate tw:font-bold">
              {{ option.label }}
            </span>

            <span class="tw:block tw:text-sm tw:text-secondary-text">
              {{ formatCost(option.cost) }}
            </span>
          </label>

          <FieldBaseCheckbox
            v-model="selected[option.key]"
            :name="option.inputId"
            variant="switch"
            size="lg"
          />
        </CardBase>
      </li>
    </ul>

    <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:md:grid-cols-2">
      <AdsAssemblyVideoCreditStatCard
        icon="tabler:circles"
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

    <template #cancel>
      {{ $t("global.cancel") }}
    </template>

    <template #continue>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.scripts.content-ready-modal.confirm",
        )
      }}
    </template>
  </ModalGeneric>
</template>
