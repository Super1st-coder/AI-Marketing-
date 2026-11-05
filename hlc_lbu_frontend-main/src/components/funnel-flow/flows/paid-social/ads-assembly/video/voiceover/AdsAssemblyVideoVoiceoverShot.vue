<script setup lang="ts">
import {
  VideoScriptShot,
  VideoVoice,
  VideoVoiceoverClip,
} from "@/services/funnel-flow/paid-social/VideoApi";

const props = defineProps<{
  shot: VideoScriptShot;
  /**
   * The audio generated for the shot: speech, or room tone when the shot has
   * no line. Missing until it's generated.
   */
  clip?: VideoVoiceoverClip;
  /** The voice the speech was generated with. */
  voice?: VideoVoice;
  /** Whether generating the shot's audio failed. */
  failed?: boolean;
  /** Identifies the clip in the player. */
  playerKey: string;
}>();

const { src: audioSrc, refresh: refreshAudioSrc } = useStoredFileSrc(() => ({
  storage_key: props.clip?.storage_key,
  storage_url: props.clip?.storage_path,
}));
</script>

<template>
  <Accordion>
    <template #customTitle>
      <div class="tw:flex tw:min-w-0 tw:flex-wrap tw:items-center tw:gap-2">
        <span class="tw:font-semibold">
          {{
            $t("funnel-flow.paid-social.ads.video.scripts.shot.title", {
              number: shot.index,
            })
          }}
        </span>

        <Chip color="secondary" variant="label" size="md" class="tw:truncate">
          {{
            $t("funnel-flow.paid-social.ads.video.scripts.shot.time-range", {
              start: formatNumberValue(shot.start_s, DEFAULT_NUMBER_LOCALE),
              end: formatNumberValue(shot.end_s, DEFAULT_NUMBER_LOCALE),
            })
          }}
        </Chip>

        <Chip
          v-if="shot.emotion"
          color="secondary"
          variant="label"
          size="md"
          uppercase
        >
          {{ shot.emotion }}
        </Chip>

        <Chip
          v-if="failed"
          color="error"
          variant="label"
          size="md"
          leftIcon="tabler:alert-circle"
          uppercase
        >
          {{ $t("funnel-flow.paid-social.ads.video.voiceover.shot.failed") }}
        </Chip>

        <span class="tw:text-xs tw:text-secondary-text">
          "{{ shot.line }}"
        </span>
      </div>
    </template>

    <div class="tw:flex tw:flex-col tw:gap-6">
      <AdsAssemblyVideoVoiceoverShotDetail
        :title="$t('funnel-flow.paid-social.ads.video.voiceover.shot.line')"
      >
        "{{ shot.line }}"
      </AdsAssemblyVideoVoiceoverShotDetail>

      <AdsAssemblyVideoVoiceoverShotDetail
        :title="$t('funnel-flow.paid-social.ads.video.voiceover.shot.scene')"
      >
        {{ shot.scene }}
      </AdsAssemblyVideoVoiceoverShotDetail>

      <Alert v-if="failed" type="error">
        {{
          $t(
            "funnel-flow.paid-social.ads.video.voiceover.shot.failed-description",
          )
        }}
      </Alert>

      <!-- Room tone has no voice -->
      <AdsAssemblyVideoVoiceoverVoice
        v-else-if="clip?.kind === 'AMBIENT'"
        :name="$t('funnel-flow.paid-social.ads.video.voiceover.shot.ambient')"
        :src="audioSrc"
        :playerKey="playerKey"
        @error="refreshAudioSrc"
      />

      <AdsAssemblyVideoVoiceoverVoice
        v-else-if="clip && voice"
        :name="voice.name"
        :src="audioSrc"
        :playerKey="playerKey"
        @error="refreshAudioSrc"
      />

      <div
        v-else
        class="tw:flex tw:items-center tw:gap-2 tw:rounded-md tw:border tw:border-gray-200 tw:bg-gray-100 tw:px-3 tw:py-2 tw:text-sm tw:font-medium tw:text-gray-500 tw:uppercase"
      >
        <Icon
          icon="tabler:microphone-off"
          class="tw:text-xl"
          aria-hidden="true"
        />

        {{ $t("funnel-flow.paid-social.ads.video.voiceover.shot.voiceless") }}
      </div>
    </div>
  </Accordion>
</template>
