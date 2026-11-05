<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";
import VideoApi, {
  GenerateVideoStoryboardResponse,
  VideoScriptVariant,
  VideoVisualDirectionRequest,
  VideoVisualDirectionVerdict,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { getVariantAnchorUrl } from "./storyboardShotImages";

const props = defineProps<{
  variant: VideoScriptVariant;
}>();

const emit = defineEmits<{
  /** The variant's frames, regenerated under the direction. */
  applied: [storyboard: GenerateVideoStoryboardResponse];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();
const { refresh: refreshCredits } = useVideoCredits();

const schema = computed(() =>
  toTypedSchema(
    object({
      direction: string().trim().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, values } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    direction: "",
  },
});

const generalErrorMessage = ref<string>();

/** Luca's verdict on the direction, shown until the direction changes. */
const verdict = ref<VideoVisualDirectionVerdict>();

/**
 * What "Apply Changes" charges (HL-2751): every frame again plus the scene rewrite. Shown on
 * the button once the direction is validated; undefined while unknown, so the button falls
 * back to its plain label instead of showing a wrong number.
 */
const applyCost = ref<number>();

// A verdict and its price only apply to the direction they were given for, so editing it
// asks for a new validation
watch(
  () => values.direction,
  () => {
    verdict.value = undefined;
    applyCost.value = undefined;
  },
);

async function loadApplyCost(direction: string) {
  try {
    // The storyboard only exists in Full Video, and neither the frames nor the rewrite depend
    // on the video model, so the defaults price it exactly
    const estimate = await VideoApi.estimateVariants(
      [props.variant],
      "FULL_VIDEO",
      null,
      store.currentSet?.id ?? null,
      direction,
      store.currentAd?.ad_id ?? null,
    );
    const frames = estimate.storyboard;
    const rewrite = estimate.direction;
    if (frames.priced && rewrite?.priced) {
      applyCost.value = frames.lucas + rewrite.lucas;
    }
  } catch (error) {
    // Not blocking: without a price the button just shows its plain label
    console.error("Failed to estimate the visual direction cost:", error);
  }
}

function createRequest(direction: string): VideoVisualDirectionRequest {
  if (!store.currentAd || !store.currentSet) {
    throw new Error("There is no current ad");
  }

  return {
    id_adset: store.currentSet.id,
    id_ad: store.currentAd.ad_id,
    brand_id: String(store.brandId),
    direction,
    variant: props.variant,
    siblings: Object.values(store.currentAd?.draft.variants ?? {}).filter(
      (variant) => variant.variant_id !== props.variant.variant_id,
    ),
  };
}

// Regenerates every frame of the variant. Some frames can fail without the
// request failing, but if every one did there's nothing to show
async function applyDirection(direction: string) {
  // Every frame is generated again, the protagonist included, so the
  // variant's anchor frame is sent to keep the same person
  const anchorUrl = await getVariantAnchorUrl(
    store.currentAd?.draft.variants[props.variant.variant_id],
  );

  const storyboard = await VideoApi.applyVisualDirection({
    ...createRequest(direction),
    variant_anchors: anchorUrl
      ? { [props.variant.variant_id]: anchorUrl }
      : undefined,
  });

  // Billed even when no frame came back, so the balance is read before the check
  void refreshCredits();

  if (!storyboard.frames[props.variant.variant_id]?.length) {
    throw new Error("No frame could be generated with the visual direction");
  }

  // The backend saves the new frames by itself, but not the direction they
  // were generated with, which the next steps need.
  if (store.currentAd && storyboard.draft_saved) {
    await VideoApi.saveDraft({
      ad_id: store.currentAd.ad_id,
      variants: {
        [props.variant.variant_id]: { visual_direction: direction },
      },
    });
    await store.refetchCurrentAd();
  }

  emit("applied", storyboard);
  isOpen.value = false;
}

// The first submit validates the direction and shows the verdict. The next one
// applies it. A warning doesn't block, the user decides whether to apply it
const onSubmit = handleSubmit(async (values) => {
  generalErrorMessage.value = undefined;

  if (!verdict.value) {
    try {
      ({ verdict: verdict.value } = await VideoApi.validateVisualDirection(
        createRequest(values.direction),
      ));
      void loadApplyCost(values.direction);
    } catch (error) {
      console.error("Failed to validate visual direction:", error);
      const billingKey = videoCreditsErrorKey(error);
      if (billingKey) void refreshCredits();
      generalErrorMessage.value = t(
        billingKey ??
          "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.errors.validation-failed",
      );
    }
    return;
  }

  try {
    await applyDirection(values.direction);
  } catch (error) {
    console.error("Failed to apply visual direction:", error);
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    generalErrorMessage.value = t(
      billingKey ??
        "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.errors.apply-failed",
    );
  }
});
</script>

<template>
  <!-- Locked while submitting: no close button, no closing on click outside -->
  <Modal
    v-model="isOpen"
    as="form"
    :maxWidth="750"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    v-slot="{ close }"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{ variant.title }}

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.description",
          )
        }}
      </template>
    </ModalHeader>

    <ModalBody class="tw:flex tw:flex-col tw:gap-6">
      <FieldTextarea
        name="direction"
        :label="
          $t(
            'funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.direction.label',
          )
        "
        :placeholder="
          $t(
            'funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.direction.placeholder',
          )
        "
        :rows="4"
        :disabled="isSubmitting"
        speechRecognition
      >
        <template #hint>
          {{
            $t(
              "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.direction.hint",
            )
          }}
        </template>
      </FieldTextarea>

      <Alert v-if="verdict === 'WARNING'" type="warning">
        {{
          $t(
            "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.verdicts.WARNING",
          )
        }}
      </Alert>

      <Alert v-else-if="verdict === 'OK'" type="success">
        {{
          $t(
            "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.verdicts.OK",
          )
        }}
      </Alert>

      <Alert v-if="generalErrorMessage" type="error" autoScroll>
        {{ generalErrorMessage }}
      </Alert>
    </ModalBody>

    <ModalFooter>
      <Button
        color="secondary"
        variant="outlined"
        type="button"
        :disabled="isSubmitting"
        @click="close"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button type="submit" leftIcon="custom:hi-luca" :isLoading="isSubmitting">
        {{
          verdict
            ? applyCost === undefined
              ? $t(
                  "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.apply",
                )
              : $t(
                  "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.apply-cost",
                  { cost: applyCost },
                )
            : $t(
                "funnel-flow.paid-social.ads.video.storyboard.visual-direction-modal.validate",
              )
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
