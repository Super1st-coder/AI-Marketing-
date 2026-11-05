<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { boolean, object, string } from "yup";
import VideoApi, {
  VideoScriptShot,
  VideoScriptVariant,
  VideoStoryboardFrame,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { SegmentsClipVersion, getStoredFileUrl } from "./segmentFiles";

const props = defineProps<{
  variant: VideoScriptVariant;
  shot: VideoScriptShot;
  /**
   * The version being edited. Missing when the shot has no clip yet, e.g. it
   * failed: then the clip starts from the storyboard image, like a retry.
   */
  version?: SegmentsClipVersion;
  /** The shot's storyboard frame, for models that take no video reference. */
  frame?: VideoStoryboardFrame;
  /** Settings' video model. The default one when null. */
  modelId: string | null;
  modelName?: string;
  /** Whether the model can start from the current clip. */
  acceptsVideoReference: boolean;
}>();

const emit = defineEmits<{
  /** The new clip is in the draft, which was loaded again. */
  applied: [scene: string];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();

// Needs a clip to start from, and a model that takes one
const canUseCurrentClip = computed(
  () => props.acceptsVideoReference && Boolean(props.version),
);

const schema = computed(() =>
  toTypedSchema(
    object({
      scene_override: string().trim().required(t("forms.required-field")),
      feedback: string().trim().default(""),
      use_current_as_reference: boolean().default(true),
    }),
  ),
);

const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    // Starts from the scene of the version being edited, so a feedback-only
    // edit keeps it
    scene_override: props.version?.scene || props.shot.scene,
    feedback: "",
    use_current_as_reference: canUseCurrentClip.value,
  },
});

/**
 * What the edit charges: the shot's rendered seconds, priced as the backend
 * charges them. Undefined while unknown, so the button shows its plain label
 * instead of a wrong number.
 */
const cost = ref<number>();

onMounted(async () => {
  try {
    // A variant with only this shot prices just its clip
    const estimate = await VideoApi.estimateVariants(
      [{ ...props.variant, shots: [props.shot] }],
      "FULL_VIDEO",
      props.modelId,
      null,
      null,
      store.currentAd?.ad_id ?? null,
    );
    if (estimate.video.priced) cost.value = estimate.video.lucas;
  } catch (error) {
    // Not blocking: the backend refuses the edit if credits run short
    console.error("Failed to estimate the clip cost:", error);
  }
});

const generalErrorMessage = ref<string>();

const onSubmit = handleSubmit(async (formValues) => {
  generalErrorMessage.value = undefined;

  try {
    if (!store.currentAd || !store.currentSet) {
      throw new Error("There is no current ad");
    }

    const currentClip =
      canUseCurrentClip.value && formValues.use_current_as_reference
        ? props.version?.clip
        : undefined;

    // The provider downloads both, so the links have to be fresh ones
    const [currentVideoUrl, imageUrl] = await Promise.all([
      currentClip ? getStoredFileUrl(currentClip) : null,
      props.frame ? getStoredFileUrl(props.frame) : null,
    ]);

    await VideoApi.editSegmentShot({
      id_adset: store.currentSet.id,
      ad_index: store.currentAdIndex,
      id_ad: store.currentAd.ad_id,
      brand_id: String(store.brandId),
      variant: props.variant,
      shot_index: props.shot.index,
      model: props.modelId,
      scene_override: formValues.scene_override,
      feedback: formValues.feedback,
      current_video_url: currentVideoUrl,
      // Also sent with the clip: it's what models without a video reference
      // start from
      image_url: imageUrl,
    });

    // Load the draft the backend saved the new clip to
    await store.refetchCurrentAd();

    emit("applied", formValues.scene_override);
    isOpen.value = false;
  } catch (error) {
    console.error("Failed to edit the clip:", error);
    // Out of credits, billing down... get their own message
    generalErrorMessage.value = t(
      videoCreditsErrorKey(error) ??
        "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-modal.errors.edit-failed",
    );
  }
});
</script>

<template>
  <!-- Locked while submitting: no close button, no closing on click outside -->
  <Modal
    v-model="isOpen"
    as="form"
    :maxWidth="700"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    v-slot="{ close }"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      {{
        $t(
          "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.title",
          { number: shot.index },
        )
      }}

      <template #description>
        {{
          $t(
            canUseCurrentClip
              ? "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-modal.description"
              : "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-modal.description-frame",
            { model: modelName },
          )
        }}
      </template>
    </ModalHeader>

    <ModalBody class="tw:flex tw:flex-col tw:gap-6">
      <FieldTextarea
        name="scene_override"
        required
        :label="
          $t(
            'funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.scene.label',
          )
        "
        :placeholder="
          $t(
            'funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.scene.placeholder',
          )
        "
        :rows="2"
        :disabled="isSubmitting"
        speechRecognition
      />

      <FieldTextarea
        name="feedback"
        :label="
          $t(
            'funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.feedback.label',
          )
        "
        :placeholder="
          $t(
            'funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.feedback.placeholder',
          )
        "
        :rows="2"
        :disabled="isSubmitting"
        speechRecognition
      />

      <CardBase
        class="tw:flex tw:items-center tw:justify-between tw:gap-3 tw:p-4"
        borderRadius="md"
        :shadow="false"
        :disabled="isSubmitting"
      >
        <label for="use_current_as_reference" class="tw:cursor-pointer">
          <span class="tw:mb-1 tw:block tw:font-bold">
            {{
              $t(
                "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-modal.use-reference.label",
              )
            }}
          </span>

          <span class="tw:block tw:text-sm tw:text-secondary-text">
            {{
              $t(
                !version
                  ? "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-modal.use-reference.no-clip"
                  : acceptsVideoReference
                    ? "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-modal.use-reference.description"
                    : "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-modal.use-reference.unsupported",
                { model: modelName },
              )
            }}
          </span>
        </label>

        <!-- The checkbox uses its `name` as the input id -->
        <FieldCheckbox
          name="use_current_as_reference"
          variant="switch"
          size="lg"
          :disabled="isSubmitting || !canUseCurrentClip"
        />
      </CardBase>

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

      <Button type="submit" :isLoading="isSubmitting">
        {{
          cost === undefined
            ? $t(
                "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.apply",
              )
            : $t(
                "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-modal.apply-with-cost",
                { cost: cost.toFixed(2) },
              )
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
