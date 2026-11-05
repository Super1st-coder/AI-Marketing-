<script setup lang="ts">
import {
  VideoScriptShot,
  VideoSegment,
  VideoStoryboardFrame,
  VideoVoiceoverClip,
} from "@/services/funnel-flow/paid-social/VideoApi";
import { getFieldFilesMimeTypes } from "@/components/forms/base/FieldFiles.vue";
import {
  SegmentsClipFailure,
  SegmentsFileValue,
  SegmentsShotEditLock,
  openStoredFile,
} from "./segmentFiles";

const props = defineProps<{
  shot: VideoScriptShot;
  /** Position of the shot in the form's `clips`. */
  fieldIndex: number;
  isScriptsOnly: boolean;
  /** The clip saved in the draft: generated, or uploaded by the user. */
  savedClip?: VideoSegment;
  /** The shot's voiceover, in Scripts Only. */
  audioClip?: VideoVoiceoverClip;
  voiceName?: string;
  /** Why the shot's clip couldn't be generated, if it failed. */
  failure?: SegmentsClipFailure;
  /** Why "Edit shot" is disabled, besides `disabled`. Missing when it isn't. */
  editLock?: SegmentsShotEditLock;
  /** Scripts Only: whether its audio can be generated again. */
  canRegenerateAudio?: boolean;
  isRegeneratingAudio?: boolean;
  /** Why the last audio regeneration failed. */
  audioErrorMessage?: string;
  /** Whether the failed clip is being generated again. */
  isRetrying?: boolean;
  /** Why the last retry failed. */
  retryErrorMessage?: string;
  /** The shot's storyboard frame. */
  frame?: VideoStoryboardFrame;
  /** Also disables "Retry", e.g. while another clip is retried. */
  disabled?: boolean;
}>();

const emit = defineEmits<{
  /** Generates the failed clip again. */
  retry: [];
  /** Opens the shot's generated versions, to edit them. */
  editShot: [];
  /** Generates the shot's audio again. Scripts Only. */
  regenerateAudio: [];
}>();

const { t } = useI18n();

const { value, setValue } = useField<SegmentsFileValue>(
  () => `clips.${props.fieldIndex}`,
);

const isOpen = ref(false);

const pickedClipSrc = useObjectUrl(() =>
  value.value instanceof Blob ? value.value : undefined,
);

// The saved clip shows unless the user removed the one they had uploaded
const visibleSavedClip = computed(() =>
  typeof value.value === "string" ||
  (value.value === null && !props.savedClip?.uploaded)
    ? props.savedClip
    : undefined,
);
const { src: savedClipSrc, refresh: refreshSavedClipSrc } = useStoredFileSrc(
  () => ({
    storage_key: visibleSavedClip.value?.storage_key,
    storage_url: visibleSavedClip.value?.storage_path,
  }),
);
const { src: audioSrc, refresh: refreshAudioSrc } = useStoredFileSrc(() => ({
  storage_key: props.audioClip?.storage_key,
  storage_url: props.audioClip?.storage_path,
}));

// Hidden once the user picks a clip to replace the one that failed
const shownFailure = computed(() =>
  value.value === null ? props.failure : undefined,
);

const clipSrc = computed(() =>
  value.value instanceof Blob ? pickedClipSrc.value : savedClipSrc.value,
);

// A picked clip's link doesn't expire, only the saved one's does
function handleClipError() {
  if (!(value.value instanceof Blob)) refreshSavedClipSrc();
}

// The file the user uploaded, or picked and hasn't saved yet
const file = computed(() => {
  if (value.value instanceof Blob) {
    return {
      name: value.value instanceof File ? value.value.name : "",
      size: value.value.size,
      src: pickedClipSrc.value,
    };
  }

  if (typeof value.value === "string") {
    return {
      name: props.savedClip?.file_name ?? "",
      size: props.savedClip?.file_size,
      src: savedClipSrc.value,
    };
  }

  return undefined;
});

const fileInput = useTemplateRef("fileInput");

// The same videos as the final cut
const acceptedTypes = getFieldFilesMimeTypes(
  ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_ACCEPTED_FORMATS,
);

const pickError = ref<string>();

// Like `FieldFiles`: a video with the wrong format or size isn't set, and the
// error shows instead. Picking a valid one clears it
function pick(picked: File) {
  if (!acceptedTypes.includes(picked.type)) {
    pickError.value = t("forms.file-upload.file-format-error", {
      formats: ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_ACCEPTED_FORMATS.map(
        (format) => t(`forms.file-upload.formats.${format}`),
      ).join(", "),
    });
    return;
  }

  if (picked.size > ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_MAX_FILE_SIZE_BYTES) {
    pickError.value = t("forms.file-upload.file-size-error", {
      maxSize: formatFileSize(
        ADS_ASSEMBLY_VIDEO_REFERENCE_VIDEO_MAX_FILE_SIZE_BYTES,
      ),
    });
    return;
  }

  pickError.value = undefined;
  setValue(picked);
}

function handleChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const picked = input.files?.[0];
  if (picked) pick(picked);
  // Picking the same file again still triggers a change
  input.value = "";
}

// The shot's main asset: its clip, or else its voiceover (Scripts Only) or its
// storyboard frame.
// TODO: download a zip with all of them, once the backend has an endpoint
const assetKey = computed(
  () =>
    visibleSavedClip.value?.storage_key ??
    props.audioClip?.storage_key ??
    props.frame?.storage_key ??
    undefined,
);
</script>

<template>
  <Accordion v-model="isOpen">
    <template #customTitle>
      <div class="tw:flex tw:min-w-0 tw:flex-col tw:gap-2">
        <div class="tw:flex tw:min-w-0 tw:items-baseline tw:gap-2">
          <span class="tw:shrink-0 tw:font-semibold">
            {{
              $t("funnel-flow.paid-social.ads.video.scripts.shot.title", {
                number: shot.index,
              })
            }}
          </span>

          <span class="tw:truncate tw:text-xs tw:text-secondary-text">
            "{{ shot.line }}"
          </span>
        </div>

        <div class="tw:flex tw:flex-wrap tw:gap-2">
          <Chip color="secondary" variant="label" size="md">
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
            v-if="shownFailure"
            color="error"
            variant="label"
            size="md"
            leftIcon="tabler:alert-circle"
            uppercase
          >
            {{
              $t("funnel-flow.paid-social.ads.refine.editor.segments.failed")
            }}
          </Chip>
        </div>
      </div>
    </template>

    <div v-if="isOpen" class="tw:flex tw:flex-col tw:gap-4 tw:sm:flex-row">
      <!-- 9:16, like the video -->
      <div
        class="tw:flex tw:aspect-[9/16] tw:w-26 tw:shrink-0 tw:items-center tw:justify-center tw:self-start tw:overflow-hidden tw:rounded-md tw:bg-gray-100"
      >
        <video
          v-if="clipSrc"
          :src="clipSrc"
          class="tw:h-full tw:w-full tw:bg-black tw:object-contain"
          controls
          playsinline
          preload="metadata"
          @error="handleClipError"
        />

        <!-- Scripts Only has no generated clips, only the uploaded ones -->
        <Icon
          v-else
          :icon="isScriptsOnly ? 'tabler:video-off' : 'tabler:video'"
          class="tw:text-[48px] tw:text-gray-500"
          aria-hidden="true"
        />
      </div>

      <div class="tw:flex tw:min-w-0 tw:grow tw:flex-col tw:gap-6">
        <AdsAssemblyVideoVoiceoverShotDetail
          :title="$t('funnel-flow.paid-social.ads.refine.editor.segments.line')"
        >
          "{{ shot.line }}"
        </AdsAssemblyVideoVoiceoverShotDetail>

        <AdsAssemblyVideoVoiceoverShotDetail
          :title="$t('funnel-flow.paid-social.ads.video.voiceover.shot.scene')"
        >
          {{ shot.scene }}
        </AdsAssemblyVideoVoiceoverShotDetail>

        <Alert v-if="shownFailure" type="error">
          {{
            retryErrorMessage ??
            $t(
              `funnel-flow.paid-social.ads.refine.editor.segments.failure-reasons.${shownFailure}`,
            )
          }}

          <!-- A shot whose storyboard frame is missing has to retry it first,
            in the Storyboard step. The label doesn't wrap when the message is
            long -->
          <template v-if="shownFailure !== 'missing-frame'" #actions>
            <Button
              class="tw:whitespace-nowrap"
              color="secondary"
              variant="outlined"
              size="sm"
              leftIcon="tabler:refresh"
              type="button"
              :uppercase="false"
              :isLoading="isRetrying"
              :disabled="disabled"
              @click="emit('retry')"
            >
              {{ $t("global.retry") }}
            </Button>
          </template>
        </Alert>

        <Alert v-if="isScriptsOnly && audioErrorMessage" type="error">
          {{ audioErrorMessage }}
        </Alert>

        <AdsAssemblyVideoVoiceoverVoice
          v-if="isScriptsOnly && audioClip"
          :name="
            audioClip.kind === 'AMBIENT'
              ? $t('funnel-flow.paid-social.ads.video.voiceover.shot.ambient')
              : (voiceName ?? audioClip.voice_id)
          "
          :src="audioSrc"
          :playerKey="`segments:${shot.index}`"
          @error="refreshAudioSrc"
        />

        <div class="tw:flex tw:flex-wrap tw:gap-3">
          <!-- No modal: the same line and voice, generated again -->
          <Button
            v-if="isScriptsOnly"
            color="secondary"
            variant="outlined"
            type="button"
            size="sm"
            :uppercase="false"
            :isLoading="isRegeneratingAudio"
            :disabled="disabled || !canRegenerateAudio"
            @click="emit('regenerateAudio')"
          >
            {{
              $t(
                "funnel-flow.paid-social.ads.refine.editor.segments.regenerate-audio",
              )
            }}
          </Button>

          <!-- Says why it's disabled, unless it's only while something else
            runs -->

          <Tooltip v-else :disabled="!editLock" placement="top" :maxWidth="260">
            <Button
              color="secondary"
              variant="outlined"
              type="button"
              size="sm"
              leftIcon="tabler:pencil"
              :uppercase="false"
              :disabled="disabled || Boolean(editLock)"
              @click="emit('editShot')"
            >
              {{
                $t(
                  "funnel-flow.paid-social.ads.refine.editor.segments.edit-shot",
                )
              }}
            </Button>

            <template #content>
              {{
                $t(
                  `funnel-flow.paid-social.ads.refine.editor.segments.edit-shot-locks.${editLock}`,
                )
              }}
            </template>
          </Tooltip>

          <!-- One clip per shot: the uploaded one has to be removed first -->
          <Button
            color="secondary"
            variant="outlined"
            type="button"
            size="sm"
            leftIcon="tabler:upload"
            :uppercase="false"
            :disabled="disabled || value !== null"
            @click="fileInput?.click()"
          >
            {{
              $t(
                "funnel-flow.paid-social.ads.refine.editor.segments.upload-clip",
              )
            }}
          </Button>

          <Button
            variant="label"
            type="button"
            size="sm"
            leftIcon="tabler:download"
            :uppercase="false"
            :disabled="!assetKey"
            @click="openStoredFile(assetKey!)"
          >
            {{
              $t(
                "funnel-flow.paid-social.ads.refine.editor.segments.download-shot-assets",
                { number: shot.index },
              )
            }}
          </Button>

          <input
            ref="fileInput"
            type="file"
            :accept="acceptedTypes.join(',')"
            hidden
            @change="handleChange"
          />
        </div>

        <AdsAssemblyEditorOverlaySegmentsFile
          v-if="file"
          :name="file.name"
          :size="file.size"
          :src="file.src"
          :disabled="disabled"
          @remove="setValue(null)"
          @error="handleClipError"
        />

        <FieldError v-if="pickError">{{ pickError }}</FieldError>
      </div>
    </div>
  </Accordion>
</template>
