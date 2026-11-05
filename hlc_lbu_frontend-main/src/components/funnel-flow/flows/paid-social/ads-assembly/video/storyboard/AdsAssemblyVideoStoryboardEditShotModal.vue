<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { boolean, object, string } from "yup";
import VideoApi, {
  EditVideoStoryboardShotRequest,
  EditVideoStoryboardShotResponse,
  VideoScriptShot,
  VideoScriptVariant,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { StoryboardShotImage } from "./storyboardShotImages";

const props = defineProps<{
  variant: VideoScriptVariant;
  shot: VideoScriptShot;
  /** The version being edited. */
  image?: StoryboardShotImage;
}>();

const emit = defineEmits<{
  applied: [response: EditVideoStoryboardShotResponse];
}>();

const isOpen = defineModel<boolean>({ required: true });

const { t, locale } = useI18n();
const store = useFunnelPaidSocialAdsAssemblyStore();
const notificationStore = useNotificationStore();

const hasCurrentImage = computed(() => Boolean(props.image?.image_url));

// What "Apply changes" charges: one new frame, priced as the storyboard prices this shot (the
// backend charges an edit as one storyboard image). Shown on the button, as PRD 2.4.C asks
// ("Apply changes · Cost {X} lucas"). `undefined` while loading or unpriced, and then the
// button can't charge: the user never pays for an edit they weren't shown the price of
const cost = ref<number>();
const isPricing = ref(true);

onMounted(async () => {
  try {
    const estimate = await VideoApi.estimateVariants(
      [{ ...props.variant, shots: [props.shot] }],
      store.currentAd?.draft.settings?.production_mode ?? "FULL_VIDEO",
      store.currentAd?.draft.settings?.model ?? null,
      null,
      null,
      store.currentAd?.ad_id ?? null,
    );
    if (estimate.storyboard.priced) cost.value = estimate.storyboard.lucas;
  } catch (error) {
    console.error("Failed to estimate the shot edit cost:", error);
  } finally {
    isPricing.value = false;
  }
});

// The company's balance. While it's unknown nothing is blocked here: the backend refuses the
// edit if credits run short
const { balance: creditsBalance, refresh: refreshCredits } = useVideoCredits();
const isOverBalance = computed(() => {
  const available = creditsBalance.value?.available;
  return (
    available !== undefined &&
    cost.value !== undefined &&
    cost.value > available
  );
});

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
    // edit keeps it. Same fallback as the shot modal's "Current scene"
    scene_override: props.image?.scene || props.shot.scene,
    feedback: "",
    use_current_as_reference: hasCurrentImage.value,
  },
});

const generalErrorMessage = ref<string>();

const onSubmit = handleSubmit(async (formValues) => {
  generalErrorMessage.value = undefined;

  try {
    if (!store.currentAd || !store.currentSet) {
      throw new Error("There is no current ad");
    }

    const useCurrentAsReference =
      hasCurrentImage.value && formValues.use_current_as_reference;

    const currentImageUrl = props.image?.storage_key
      ? (await VideoApi.getDownloadUrl(props.image.storage_key)).url
      : (props.image?.image_url ?? null);

    const request: EditVideoStoryboardShotRequest = {
      id_adset: store.currentSet.id,
      ad_index: store.currentAdIndex,
      id_ad: store.currentAd.ad_id,
      brand_id: String(store.brandId),
      variant: props.variant,
      shot_index: props.shot.index,
      scene_override: formValues.scene_override,
      feedback: formValues.feedback,
      use_current_as_reference: useCurrentAsReference,
      current_image_url: currentImageUrl,
      // TODO: send the protagonist's base image once the storyboard has one
      base_image_url: null,
    };

    const response = await VideoApi.editStoryboardShot(request);

    // The edit was charged: the counter shows it without a reload
    void refreshCredits();

    // Load the draft the backend saved the new frame to
    await store.refetchCurrentAd();

    notificationStore.display({
      type: "success",
      title: t(
        "funnel-flow.paid-social.ads.video.storyboard.toasts.shot-updated",
        { number: props.shot.index },
      ),
    });

    emit("applied", response);
    isOpen.value = false;
  } catch (error) {
    console.error("Failed to edit the shot image:", error);
    // Out of credits or billing down: the balance is read again
    const billingKey = videoCreditsErrorKey(error);
    if (billingKey) void refreshCredits();
    generalErrorMessage.value = t(
      billingKey ??
        "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.errors.edit-failed",
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
            "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.description",
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
                "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.use-reference.label",
              )
            }}
          </span>

          <span class="tw:block tw:text-sm tw:text-secondary-text">
            {{
              $t(
                "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.use-reference.description",
              )
            }}
          </span>
        </label>

        <!-- The checkbox uses its `name` as the input id -->
        <FieldCheckbox
          name="use_current_as_reference"
          variant="switch"
          size="lg"
          :disabled="isSubmitting || !hasCurrentImage"
        />
      </CardBase>

      <Alert v-if="isOverBalance" type="warning">
        {{
          $t(
            "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.over-balance",
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

      <Button
        type="submit"
        :isLoading="isSubmitting || isPricing"
        :disabled="cost === undefined || isOverBalance"
        data-testid="video-storyboard-edit-shot-apply"
      >
        {{
          cost === undefined
            ? $t(
                "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.apply",
              )
            : $t(
                "funnel-flow.paid-social.ads.video.storyboard.edit-shot-modal.apply-cost",
                { cost: formatNumberValue(cost, locale) },
              )
        }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
