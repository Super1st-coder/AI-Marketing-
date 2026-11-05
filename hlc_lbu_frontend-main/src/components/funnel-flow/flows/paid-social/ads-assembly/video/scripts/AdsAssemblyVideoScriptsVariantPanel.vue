<script setup lang="ts">
import VideoApi, {
  VIDEO_SHOT_DELIVERY_MODES,
  VIDEO_SHOT_TYPES,
  VideoScriptVariant,
  VideoShotDeliveryMode,
  VideoShotType,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, mixed, object, string } from "yup";
import { videoScriptScoreColorClass } from "../videoScriptScore";

const props = defineProps<{
  variant: VideoScriptVariant;
  isSaving?: boolean;
  isGeneratingStoryboard?: boolean;
  /** Disables the footer actions while any save or generation is running. */
  isBusy?: boolean;
  errorMessage?: string;
  /** LUCA that saving charges (it re-scores the variant); shown when known. */
  rescoreCost?: number;
  /** LUCA that "Generate Storyboard" charges, for every variant; shown on the button. */
  storyboardCost?: number;
  /**
   * Whether the button charges right away, so it needs a price first. Not in Scripts Only,
   * where it opens a window that shows the price.
   */
  isStoryboardPriceRequired?: boolean;
  isPricingStoryboard?: boolean;
}>();

const emit = defineEmits<{
  save: [];
  generateStoryboard: [];
}>();

const dirty = defineModel<boolean>("dirty", { default: false });

const store = useFunnelPaidSocialAdsAssemblyStore();
const { refresh: refreshCredits } = useVideoCredits();
const { t, te, locale } = useI18n();

const axisLabel = computed(() => {
  const key = `funnel-flow.paid-social.ads.video.scripts.axes.${props.variant.axis}`;
  return te(key) ? t(key) : props.variant.axis;
});

// The backend scores on a 0-10 scale
const score = computed(() =>
  props.variant.score === null ? null : Math.round(props.variant.score),
);

// Applied to the unrounded score
const scoreColorClass = computed(() =>
  videoScriptScoreColorClass(props.variant.score),
);

const totalDuration = computed(() =>
  Math.max(0, ...props.variant.shots.map((shot) => shot.end_s)),
);

const schema = computed(() =>
  toTypedSchema(
    object({
      strategic_angle: string().required(t("forms.required-field")),
      archetype: string().required(t("forms.required-field")),
      hook: string().required(t("forms.required-field")),
      final_cta: string().required(t("forms.required-field")),
      shots: array().of(
        object({
          line: string(),
          scene: string().required(t("forms.required-field")),
          composition: string(),
          delivery_mode: mixed<VideoShotDeliveryMode>()
            .oneOf(VIDEO_SHOT_DELIVERY_MODES)
            .required(t("forms.required-field")),
          shot_type: mixed<VideoShotType>()
            .oneOf(VIDEO_SHOT_TYPES)
            .required(t("forms.required-field")),
          emotion: string().required(t("forms.required-field")),
          on_screen_text: string(),
        }),
      ),
    }),
  ),
);

const { handleSubmit, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  keepValuesOnUnmount: true,
  resetDirtyOnSubmit: true,
  initialValues: {
    strategic_angle: props.variant.strategic_angle,
    archetype: props.variant.archetype,
    hook: props.variant.hook,
    final_cta: props.variant.final_cta,
    shots: props.variant.shots.map((shot) => ({
      line: shot.line,
      scene: shot.scene,
      composition: shot.composition,
      delivery_mode: shot.delivery_mode,
      shot_type: shot.shot_type,
      emotion: shot.emotion,
      on_screen_text: shot.on_screen_text,
    })),
  },
});

function handleGoBack() {
  store.setScreen("videoSettings");
}

watch(
  () => meta.value.dirty,
  (value) => {
    dirty.value = value;
  },
  { immediate: true },
);

const save = handleSubmit(async (values) => {
  const currentAd = store.currentAd;
  if (!currentAd || !store.currentSet) return;

  // The form only covers some fields, so the rest of the variant is kept
  const editedVariant: VideoScriptVariant = {
    ...props.variant,
    strategic_angle: values.strategic_angle,
    archetype: values.archetype,
    hook: values.hook,
    final_cta: values.final_cta,
    shots: props.variant.shots.map((shot, index) => {
      const editedShot = values.shots?.[index];
      if (!editedShot) return shot;

      return {
        ...shot,
        line: editedShot.line ?? "",
        scene: editedShot.scene,
        composition: editedShot.composition ?? "",
        delivery_mode: editedShot.delivery_mode,
        shot_type: editedShot.shot_type,
        emotion: editedShot.emotion,
        on_screen_text: editedShot.on_screen_text ?? "",
      };
    }),
    // The edit invalidates the previous score until the request below
    // resolves. Shown even if saving fails, since the content did change
    score_outdated: true,
  };

  // Save first, so the edit isn't lost if scoring fails
  await VideoApi.saveDraft({
    ad_id: currentAd.ad_id,
    variants: { [editedVariant.variant_id]: editedVariant },
  });
  await store.refetchCurrentAd();

  // Each variant is scored on its own, so only the edited one is sent
  const response = await VideoApi.scoreScripts({
    id_adset: store.currentSet.id,
    brand_id: String(store.brandId),
    variants: [editedVariant],
  });

  // Re-scoring is charged in Luca Credits
  void refreshCredits();

  await VideoApi.saveDraft({
    ad_id: currentAd.ad_id,
    variants: Object.fromEntries(
      response.variants.map((variant) => [variant.variant_id, variant]),
    ),
  });
  await store.refetchCurrentAd();
});

defineExpose({ save });
</script>

<template>
  <div class="tw:flex tw:grow tw:flex-col">
    <Container class="tw:grow tw:pb-12" :maxWidth="910">
      <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:p-6" borderRadius="md">
        <div>
          <div
            class="tw:mb-2 tw:flex tw:items-center tw:justify-between tw:gap-4"
          >
            <h3 class="tw:text-xl tw:font-bold">
              {{ variant.title }}
            </h3>

            <span
              v-if="score !== null"
              class="tw:text-sm tw:font-semibold tw:uppercase"
              :class="scoreColorClass"
            >
              {{
                $t("funnel-flow.paid-social.ads.video.scripts.score", { score })
              }}
            </span>
          </div>

          <ChipList>
            <Chip color="secondary" variant="outlined" size="lg">
              {{
                $t("funnel-flow.paid-social.ads.video.scripts.axis-chip", {
                  axis: axisLabel,
                })
              }}
            </Chip>

            <Chip color="secondary" variant="outlined" size="lg">
              {{
                $t("funnel-flow.paid-social.ads.video.scripts.archetype-chip", {
                  archetype: variant.archetype,
                })
              }}
            </Chip>

            <Chip
              color="secondary"
              variant="outlined"
              size="lg"
              leftIcon="tabler:clock"
            >
              {{
                $t("funnel-flow.paid-social.ads.video.scripts.duration-exact", {
                  duration: formatNumberValue(
                    totalDuration,
                    DEFAULT_NUMBER_LOCALE,
                  ),
                })
              }}
            </Chip>
          </ChipList>
        </div>

        <Separator />

        <div
          class="tw:grid tw:grid-cols-1 tw:gap-x-6 tw:gap-y-4 tw:md:grid-cols-2"
        >
          <FieldText
            name="strategic_angle"
            required
            :label="
              $t(
                'funnel-flow.paid-social.ads.video.scripts.strategic-angle.label',
              )
            "
          />

          <FieldText
            name="archetype"
            required
            :label="
              $t('funnel-flow.paid-social.ads.video.scripts.archetype.label')
            "
          />

          <FieldText
            name="hook"
            required
            :label="$t('funnel-flow.paid-social.ads.video.scripts.hook.label')"
          />

          <FieldText
            name="final_cta"
            required
            :label="
              $t('funnel-flow.paid-social.ads.video.scripts.final-cta.label')
            "
          />
        </div>

        <Separator />

        <div class="tw:flex tw:flex-col tw:gap-4">
          <AdsAssemblyVideoLabel icon="tabler:movie">
            <template #title>
              {{ $t("funnel-flow.paid-social.ads.video.scripts.scenes-title") }}
            </template>
          </AdsAssemblyVideoLabel>

          <AccordionList>
            <AdsAssemblyVideoScriptsShot
              v-for="(shot, index) in variant.shots"
              :key="shot.index"
              :name="`shots[${index}]`"
              :shot="shot"
            />
          </AccordionList>
        </div>
      </CardBase>

      <Alert v-if="errorMessage" type="error" autoScroll class="tw:mt-6">
        {{ errorMessage }}
      </Alert>
    </Container>

    <AdsAssemblyVideoScriptsVariantPanelFooter>
      <template #before>
        <ButtonGoBack @click="handleGoBack" />
      </template>

      <Button
        variant="label"
        :disabled="!meta.dirty || isBusy"
        :isLoading="isSaving"
        @click="emit('save')"
      >
        {{
          rescoreCost === undefined
            ? $t(
                "funnel-flow.paid-social.ads.video.scripts.footer.save-changes",
              )
            : $t(
                "funnel-flow.paid-social.ads.video.scripts.footer.save-changes-cost",
                { cost: rescoreCost },
              )
        }}
      </Button>

      <!-- Never charges without showing the price first -->
      <Button
        :disabled="
          isBusy || (isStoryboardPriceRequired && storyboardCost === undefined)
        "
        :isLoading="isGeneratingStoryboard || isPricingStoryboard"
        data-testid="video-scripts-generate-storyboard"
        @click="emit('generateStoryboard')"
      >
        {{
          storyboardCost === undefined
            ? $t(
                "funnel-flow.paid-social.ads.video.scripts.footer.generate-storyboard",
              )
            : $t(
                "funnel-flow.paid-social.ads.video.scripts.footer.generate-storyboard-cost",
                { cost: formatNumberValue(storyboardCost, locale) },
              )
        }}
      </Button>
    </AdsAssemblyVideoScriptsVariantPanelFooter>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </div>
</template>
