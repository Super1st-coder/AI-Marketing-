<script setup lang="ts">
import { VideoDraftVariant } from "@/services/funnel-flow/paid-social/VideoApi";
import { SegmentsShotClipVersions, SegmentsShotEditLock } from "./segmentFiles";

const props = defineProps<{
  variant: VideoDraftVariant;
  /** Shot `index` -> its generated versions. */
  clipVersions: Record<number, SegmentsShotClipVersions>;
  /** Shot `index` -> why it can't be edited. Missing when it can. */
  locks: Record<number, SegmentsShotEditLock>;
  /** `index` of the shot shown when it opens. */
  initialShotIndex: number;
  modelId: string | null;
  modelName?: string;
  acceptsVideoReference: boolean;
  /** Disables picking a version and editing, e.g. while one is saved. */
  isBusy?: boolean;
  /** Why picking a version failed. */
  errorMessage?: string;
}>();

const emit = defineEmits<{
  selectVersion: [shotIndex: number, versionIndex: number];
  applied: [shotIndex: number, scene: string];
}>();

const isOpen = defineModel<boolean>({ required: true });

const shots = computed(() => props.variant.shots);

const {
  currentItem: currentShot,
  currentIndex,
  move,
} = useSliderRef(
  shots,
  Math.max(
    shots.value.findIndex((shot) => shot.index === props.initialShotIndex),
    0,
  ),
);

const currentVersions = computed(() =>
  currentShot.value ? props.clipVersions[currentShot.value.index] : undefined,
);

const currentLock = computed(() =>
  currentShot.value ? props.locks[currentShot.value.index] : undefined,
);

// A shot that uses an uploaded clip doesn't show the generated one, since it
// isn't the one in the video. A shot without a clip has none, and can still be
// edited, starting from its storyboard image
const activeVersion = computed(() =>
  currentLock.value
    ? undefined
    : currentVersions.value?.history[currentVersions.value.activeIndex],
);

const currentFrame = computed(() =>
  props.variant.frames?.find(
    (frame) => frame.shot_index === currentShot.value?.index,
  ),
);

function handleSelectVersion(versionIndex: number) {
  if (!currentShot.value) return;

  emit("selectVersion", currentShot.value.index, versionIndex);
}

const isEditModalOpen = ref(false);

function handleApplied(scene: string) {
  if (!currentShot.value) return;

  emit("applied", currentShot.value.index, scene);
}
</script>

<template>
  <Modal
    v-model="isOpen"
    closeButton
    :maxWidth="1020"
    innerClass="tw:overflow-hidden"
  >
    <div v-if="currentShot" class="tw:flex tw:flex-col tw:md:flex-row">
      <!-- Clip player -->
      <div
        class="tw:flex tw:min-w-0 tw:grow tw:flex-col tw:items-center tw:gap-4 tw:p-6"
      >
        <div
          class="tw:flex tw:w-full tw:grow tw:items-center tw:justify-center tw:gap-4"
        >
          <Button
            v-if="shots.length > 1"
            class="tw:shrink-0"
            color="secondary"
            variant="outlined"
            size="sm"
            icon="tabler:chevron-left"
            type="button"
            :aria-label="
              $t(
                'funnel-flow.paid-social.ads.video.storyboard.shot-modal.previous-shot',
              )
            "
            @click="move(-1)"
          />

          <div class="tw:flex tw:grow tw:justify-center">
            <AdsAssemblyEditorOverlaySegmentsClipFrame
              class="tw:w-full"
              style="max-width: 369px"
              :clip="activeVersion?.clip"
              controls
            />
          </div>

          <Button
            v-if="shots.length > 1"
            class="tw:shrink-0"
            color="secondary"
            variant="outlined"
            size="sm"
            icon="tabler:chevron-right"
            type="button"
            :aria-label="
              $t(
                'funnel-flow.paid-social.ads.video.storyboard.shot-modal.next-shot',
              )
            "
            @click="move(1)"
          />
        </div>

        <ul v-if="shots.length > 1" class="tw:flex tw:items-center tw:gap-1">
          <li v-for="(shot, index) in shots" :key="shot.index">
            <button
              type="button"
              class="tw:block tw:size-2 tw:rounded-full tw:transition-colors"
              :class="
                index === currentIndex
                  ? 'tw:bg-gray-500'
                  : 'tw:bg-gray-300 tw:hover:bg-gray-400'
              "
              :aria-label="
                $t(
                  'funnel-flow.paid-social.ads.video.storyboard.shot-modal.go-to-shot',
                  { number: shot.index },
                )
              "
              :aria-current="index === currentIndex ? 'true' : undefined"
              @click="currentIndex = index"
            />
          </li>
        </ul>
      </div>

      <!-- Shot details -->
      <div
        class="tw:flex tw:shrink-0 tw:flex-col tw:border-t tw:border-gray-200 tw:md:w-[300px] tw:md:border-t-0 tw:md:border-l"
      >
        <div class="tw:border-b tw:border-gray-200 tw:p-6">
          <!-- Leaves room for the close button -->
          <h2 class="tw:mr-12 tw:mb-2 tw:text-xl tw:font-bold">
            {{
              $t(
                "funnel-flow.paid-social.ads.video.storyboard.shot-modal.title",
                { number: currentShot.index, total: shots.length },
              )
            }}
          </h2>

          <div class="tw:flex tw:flex-wrap tw:gap-2">
            <Chip color="secondary" variant="label" size="md">
              {{
                $t(
                  "funnel-flow.paid-social.ads.video.scripts.shot.time-range",
                  {
                    start: formatNumberValue(
                      currentShot.start_s,
                      DEFAULT_NUMBER_LOCALE,
                    ),
                    end: formatNumberValue(
                      currentShot.end_s,
                      DEFAULT_NUMBER_LOCALE,
                    ),
                  },
                )
              }}
            </Chip>

            <Chip
              v-if="currentShot.emotion"
              color="secondary"
              variant="label"
              size="md"
              uppercase
            >
              {{ currentShot.emotion }}
            </Chip>
          </div>
        </div>

        <div class="tw:flex tw:grow tw:flex-col tw:gap-4 tw:p-6">
          <div v-if="currentShot.line">
            <p
              class="tw:mb-1 tw:text-xs tw:font-semibold tw:text-secondary-text tw:uppercase"
            >
              {{
                $t(
                  "funnel-flow.paid-social.ads.video.storyboard.shot-modal.line",
                )
              }}
            </p>

            <p class="tw:text-sm">{{ currentShot.line }}</p>
          </div>

          <div class="tw:border-b tw:border-gray-200 tw:pb-4">
            <p
              class="tw:mb-1 tw:text-xs tw:font-semibold tw:text-secondary-text tw:uppercase"
            >
              {{
                $t(
                  "funnel-flow.paid-social.ads.video.storyboard.shot-modal.current-scene",
                )
              }}
            </p>

            <p class="tw:text-sm">
              {{ activeVersion?.scene || currentShot.scene }}
            </p>
          </div>

          <div v-if="currentVersions?.history.length">
            <p
              class="tw:mb-2 tw:flex tw:items-center tw:gap-1 tw:text-xs tw:font-semibold tw:text-secondary-text tw:uppercase"
            >
              <Icon
                icon="tabler:clock"
                class="tw:text-[16px]"
                aria-hidden="true"
              />

              <span>
                {{
                  $t(
                    "funnel-flow.paid-social.ads.video.storyboard.shot-modal.history",
                  )
                }}
              </span>
            </p>

            <ul class="tw:mb-2 tw:flex tw:flex-wrap tw:gap-2">
              <li
                v-for="(version, versionIndex) in currentVersions.history"
                :key="versionIndex"
              >
                <!-- A shot with an uploaded clip uses none of them -->
                <button
                  type="button"
                  class="tw:relative tw:block tw:rounded-md tw:border-2 tw:transition-colors tw:disabled:cursor-not-allowed tw:disabled:opacity-60"
                  :class="
                    !currentLock && versionIndex === currentVersions.activeIndex
                      ? 'tw:border-primary'
                      : 'tw:border-transparent tw:enabled:hover:border-gray-300'
                  "
                  style="width: 78px"
                  :aria-label="
                    $t(
                      'funnel-flow.paid-social.ads.video.storyboard.shot-modal.version-label',
                      { number: versionIndex + 1 },
                    )
                  "
                  :aria-pressed="
                    !currentLock && versionIndex === currentVersions.activeIndex
                  "
                  :disabled="Boolean(currentLock) || isBusy"
                  @click="handleSelectVersion(versionIndex)"
                >
                  <AdsAssemblyEditorOverlaySegmentsClipFrame
                    :clip="version.clip"
                    class="tw:rounded-sm"
                  />

                  <span
                    class="tw:absolute tw:bottom-2.5 tw:left-2.5 tw:rounded-full tw:bg-white tw:px-2 tw:py-[3px] tw:text-xs tw:leading-none tw:font-medium"
                    aria-hidden="true"
                  >
                    {{
                      $t(
                        "funnel-flow.paid-social.ads.video.storyboard.shot-modal.version",
                        { number: versionIndex + 1 },
                      )
                    }}
                  </span>
                </button>
              </li>
            </ul>

            <p class="tw:text-xs tw:text-secondary-text">
              {{
                $t(
                  "funnel-flow.paid-social.ads.video.storyboard.shot-modal.history-hint",
                )
              }}
            </p>
          </div>

          <Alert v-if="currentLock" type="info">
            {{
              $t(
                `funnel-flow.paid-social.ads.refine.editor.segments.shot-modal.locks.${currentLock}`,
              )
            }}
          </Alert>

          <Alert v-if="errorMessage" type="error">
            {{ errorMessage }}
          </Alert>
        </div>

        <div class="tw:border-t tw:border-gray-200 tw:p-6 tw:text-center">
          <!-- The label grows by default, which would push the icon to the edge -->
          <Button
            class="tw:mb-3 tw:w-full tw:*:grow-0"
            size="sm"
            leftIcon="tabler:pencil"
            type="button"
            :disabled="Boolean(currentLock) || isBusy"
            @click="isEditModalOpen = true"
          >
            {{
              $t(
                "funnel-flow.paid-social.ads.refine.editor.segments.shot-modal.edit-video",
              )
            }}
          </Button>

          <p class="tw:text-xs tw:text-secondary-text">
            {{
              $t(
                "funnel-flow.paid-social.ads.video.storyboard.shot-modal.edit-image-hint",
              )
            }}
          </p>
        </div>
      </div>
    </div>

    <AdsAssemblyEditorOverlaySegmentsEditShotModal
      v-if="isEditModalOpen && currentShot"
      v-model="isEditModalOpen"
      :variant="variant"
      :shot="currentShot"
      :version="activeVersion"
      :frame="currentFrame"
      :modelId="modelId"
      :modelName="modelName"
      :acceptsVideoReference="acceptsVideoReference"
      @applied="handleApplied"
    />
  </Modal>
</template>
