<script setup lang="ts">
import { VideoScriptShot } from "@/services/funnel-flow/paid-social/VideoApi";
import { StoryboardShotImage } from "./storyboardShotImages";

defineProps<{
  shot: VideoScriptShot;
  /** The frame the shot uses. */
  image?: StoryboardShotImage;
  /** Whether generating the shot's frame failed. */
  failed?: boolean;
  /** Whether the failed frame is being generated again. */
  isRetrying?: boolean;
  /** Disables "Retry", e.g. while another shot is retried. */
  retryDisabled?: boolean;
  /** Why the last retry failed. */
  retryErrorMessage?: string;
}>();

const emit = defineEmits<{
  editImage: [];
  retry: [];
}>();
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
          {{ $t("funnel-flow.paid-social.ads.video.storyboard.shot.failed") }}
        </Chip>

        <span class="tw:text-xs tw:text-secondary-text">
          "{{ shot.line }}"
        </span>
      </div>
    </template>

    <div class="tw:flex tw:flex-col tw:gap-4 tw:sm:flex-row">
      <AdsAssemblyVideoStoryboardFrame
        class="tw:w-[146px] tw:shrink-0"
        :image="image"
      />

      <div>
        <p v-if="shot.line" class="tw:mb-2 tw:font-semibold">
          "{{ shot.line }}"
        </p>

        <!-- `composition` is optional, so fall back to the visual action -->
        <p class="tw:text-sm tw:text-secondary-text">
          {{ shot.composition || shot.scene }}
        </p>

        <Alert v-if="failed" type="error" class="tw:mt-4">
          {{
            retryErrorMessage ??
            $t(
              "funnel-flow.paid-social.ads.video.storyboard.shot.failed-description",
            )
          }}

          <!-- Retry button -->
          <template #actions>
            <Button
              class="tw:whitespace-nowrap"
              color="secondary"
              variant="outlined"
              size="sm"
              leftIcon="tabler:refresh"
              type="button"
              :isLoading="isRetrying"
              :disabled="retryDisabled"
              @click="emit('retry')"
            >
              {{ $t("global.retry") }}
            </Button>
          </template>
        </Alert>

        <!-- A shot without a frame has nothing to edit -->
        <Button
          v-else
          class="tw:mt-6"
          color="secondary"
          variant="outlined"
          size="sm"
          leftIcon="tabler:pencil"
          type="button"
          @click="emit('editImage')"
        >
          {{
            $t("funnel-flow.paid-social.ads.video.storyboard.shot.edit-image")
          }}
        </Button>
      </div>
    </div>
  </Accordion>
</template>
