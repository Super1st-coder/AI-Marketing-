<script setup lang="ts">
import { ChipProps } from "@/components/chips/Chip.vue";
import {
  VIDEO_SHOT_DELIVERY_MODES,
  VIDEO_SHOT_TYPES,
  VideoScriptShot,
  VideoShotDeliveryMode,
  VideoShotType,
} from "@/services/funnel-flow/paid-social/VideoApi";

const DELIVERY_MODE_CHIPS: Record<
  VideoShotDeliveryMode,
  { color: ChipProps["color"]; icon: string }
> = {
  ON_CAMERA: { color: "primary", icon: "tabler:video" },
  VOICEOVER: { color: "info", icon: "tabler:microphone" },
  SILENT: { color: "secondary", icon: "tabler:microphone-off" },
};

const props = defineProps<{
  name: string;
  shot: VideoScriptShot;
}>();

const { t, te } = useI18n();

const line = useFieldValue<string>(() => `${props.name}.line`);
const deliveryMode = useFieldValue<VideoShotDeliveryMode>(
  () => `${props.name}.delivery_mode`,
);
const shotType = useFieldValue<VideoShotType>(() => `${props.name}.shot_type`);
const emotion = useFieldValue<string>(() => `${props.name}.emotion`);

const isOpen = ref(false);

const errors = useFormErrors();
const submitCount = useSubmitCount();

const hasError = computed(() =>
  Object.keys(errors.value).some((key) => key.startsWith(`${props.name}.`)),
);

// Open on submit when a field inside has an error, so it's visible before the
// form scrolls to it. Watching `submitCount` too reopens it on later submits
watch([hasError, submitCount], () => {
  if (hasError.value && submitCount.value > 0) {
    isOpen.value = true;
  }
});

function toKeySegment(value: string) {
  return value.toLowerCase().replaceAll("_", "-");
}

const deliveryModeChip = computed(() =>
  deliveryMode.value ? DELIVERY_MODE_CHIPS[deliveryMode.value] : undefined,
);

function getShotTypeLabel(type: string) {
  const key = `funnel-flow.paid-social.ads.video.scripts.shot.shot-types.${toKeySegment(type)}`;
  return te(key) ? t(key) : type.replaceAll("_", " ");
}

const shotTypeOptions = computed(() =>
  VIDEO_SHOT_TYPES.map((type) => ({
    value: type,
    label: getShotTypeLabel(type),
  })),
);

const deliveryModeOptions = computed(() =>
  VIDEO_SHOT_DELIVERY_MODES.map((mode) => ({
    value: mode,
    label: t(
      `funnel-flow.paid-social.ads.video.scripts.shot.delivery-modes.${toKeySegment(mode)}.option`,
    ),
  })),
);
</script>

<template>
  <Accordion v-model="isOpen">
    <template #customTitle>
      <div class="tw:flex tw:flex-wrap tw:items-center tw:gap-2">
        <span class="tw:font-semibold">
          {{
            $t("funnel-flow.paid-social.ads.video.scripts.shot.title", {
              number: shot.index,
            })
          }}
        </span>

        <Chip color="secondary" variant="label" size="md">
          {{
            $t("funnel-flow.paid-social.ads.video.scripts.shot.time-range", {
              start: formatNumberValue(shot.start_s, DEFAULT_NUMBER_LOCALE),
              end: formatNumberValue(shot.end_s, DEFAULT_NUMBER_LOCALE),
            })
          }}
        </Chip>

        <Chip
          v-if="deliveryMode && deliveryModeChip"
          :color="deliveryModeChip.color"
          :leftIcon="deliveryModeChip.icon"
          variant="label"
          size="md"
          uppercase
        >
          {{
            $t(
              `funnel-flow.paid-social.ads.video.scripts.shot.delivery-modes.${toKeySegment(deliveryMode)}.chip`,
            )
          }}
        </Chip>

        <Chip
          v-if="shotType"
          color="secondary"
          variant="label"
          size="md"
          uppercase
        >
          {{ getShotTypeLabel(shotType) }}
        </Chip>

        <Chip
          v-if="emotion"
          color="secondary"
          variant="label"
          size="md"
          uppercase
        >
          {{ emotion }}
        </Chip>

        <span class="tw:text-xs tw:text-secondary-text"> "{{ line }}" </span>
      </div>
    </template>

    <div class="tw:flex tw:flex-col tw:gap-4">
      <FieldTextarea :name="`${name}.line`" :rows="2" speechRecognition />

      <FieldTextarea
        :name="`${name}.scene`"
        required
        :label="
          $t(
            'funnel-flow.paid-social.ads.video.scripts.shot.visual-action.label',
          )
        "
        :rows="2"
        speechRecognition
      />

      <FieldTextarea
        :name="`${name}.composition`"
        :label="
          $t(
            'funnel-flow.paid-social.ads.video.scripts.shot.scene-details.label',
          )
        "
        :rows="2"
        speechRecognition
      />

      <div class="tw:grid tw:grid-cols-1 tw:gap-4 tw:xl:grid-cols-2">
        <FieldNewSelect
          :name="`${name}.delivery_mode`"
          required
          :label="
            $t(
              'funnel-flow.paid-social.ads.video.scripts.shot.delivery-mode.label',
            )
          "
          :options="deliveryModeOptions"
          :clearable="false"
        />

        <FieldNewSelect
          :name="`${name}.shot_type`"
          required
          :label="
            $t('funnel-flow.paid-social.ads.video.scripts.shot.shot-type.label')
          "
          :options="shotTypeOptions"
          :clearable="false"
        />

        <FieldText
          :name="`${name}.emotion`"
          required
          :label="
            $t('funnel-flow.paid-social.ads.video.scripts.shot.emotion.label')
          "
        />

        <FieldText
          :name="`${name}.on_screen_text`"
          :label="
            $t(
              'funnel-flow.paid-social.ads.video.scripts.shot.on-screen-text.label',
            )
          "
        />
      </div>
    </div>
  </Accordion>
</template>
