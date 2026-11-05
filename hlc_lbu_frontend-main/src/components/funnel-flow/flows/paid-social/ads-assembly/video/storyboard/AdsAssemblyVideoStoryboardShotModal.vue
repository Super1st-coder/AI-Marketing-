<script setup lang="ts">
import {
  EditVideoStoryboardShotResponse,
  VideoScriptVariant,
} from "@/services/funnel-flow/paid-social/VideoApi";
import {
  StoryboardShotImage,
  StoryboardVariantShotImages,
  getActiveShotImage,
} from "./storyboardShotImages";

const props = defineProps<{
  variant: VideoScriptVariant;
  shotImages: StoryboardVariantShotImages;
  /** `index` of the shot shown when it opens. */
  initialShotIndex: number;
}>();

const emit = defineEmits<{
  selectImage: [shotIndex: number, imageIndex: number];
  addImage: [shotIndex: number, image: StoryboardShotImage];
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

const currentShotImages = computed(() =>
  currentShot.value ? props.shotImages[currentShot.value.index] : undefined,
);

const activeImage = computed(() => getActiveShotImage(currentShotImages.value));

function handleSelectImage(imageIndex: number) {
  if (!currentShot.value) return;

  emit("selectImage", currentShot.value.index, imageIndex);
}

const isEditModalOpen = ref(false);

function handleApplied(response: EditVideoStoryboardShotResponse) {
  emit("addImage", response.shot_index, {
    image_url: response.image_url,
    scene: response.scene,
    storage_key: response.storage_key,
  });
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
      <!-- Frame viewer -->
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
            <AdsAssemblyVideoStoryboardFrame
              class="tw:w-full"
              style="max-width: 369px"
              :image="activeImage"
              :alt="
                $t('funnel-flow.paid-social.ads.video.scripts.shot.title', {
                  number: currentShot.index,
                })
              "
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
              {{ activeImage?.scene || currentShot.scene }}
            </p>
          </div>

          <div v-if="currentShotImages?.history.length">
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
                v-for="(image, imageIndex) in currentShotImages.history"
                :key="imageIndex"
              >
                <button
                  type="button"
                  class="tw:relative tw:block tw:rounded-md tw:border-2 tw:transition-colors"
                  :class="
                    imageIndex === currentShotImages.activeIndex
                      ? 'tw:border-primary'
                      : 'tw:border-transparent tw:hover:border-gray-300'
                  "
                  style="width: 78px"
                  :aria-label="
                    $t(
                      'funnel-flow.paid-social.ads.video.storyboard.shot-modal.version-label',
                      { number: imageIndex + 1 },
                    )
                  "
                  :aria-pressed="imageIndex === currentShotImages.activeIndex"
                  @click="handleSelectImage(imageIndex)"
                >
                  <AdsAssemblyVideoStoryboardFrame
                    :image="image"
                    class="tw:rounded-sm"
                  />

                  <span
                    class="tw:absolute tw:bottom-2.5 tw:left-2.5 tw:rounded-full tw:bg-white tw:px-2 tw:py-[3px] tw:text-xs tw:leading-none tw:font-medium"
                    aria-hidden="true"
                  >
                    {{
                      $t(
                        "funnel-flow.paid-social.ads.video.storyboard.shot-modal.version",
                        { number: imageIndex + 1 },
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
        </div>

        <div class="tw:border-t tw:border-gray-200 tw:p-6 tw:text-center">
          <!-- The label grows by default, which would push the icon to the edge -->
          <Button
            class="tw:mb-3 tw:w-full tw:*:grow-0"
            size="sm"
            leftIcon="tabler:pencil"
            type="button"
            @click="isEditModalOpen = true"
          >
            {{
              $t(
                "funnel-flow.paid-social.ads.video.storyboard.shot-modal.edit-image",
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

    <AdsAssemblyVideoStoryboardEditShotModal
      v-if="isEditModalOpen && currentShot"
      v-model="isEditModalOpen"
      :variant="variant"
      :shot="currentShot"
      :image="activeImage"
      @applied="handleApplied"
    />
  </Modal>
</template>
