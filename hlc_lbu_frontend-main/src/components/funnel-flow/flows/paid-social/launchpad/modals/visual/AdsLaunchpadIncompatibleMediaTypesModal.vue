<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });

const maximumSelectable = ref(10);

// Mock video data
const videos = ref([{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }, { id: 5 }]);

const selectedVideoIds = ref<number[]>([1]);
const videoSelection = useIdSelection(selectedVideoIds);

// Mock image data
const images = ref([
  { id: 1 },
  { id: 2 },
  { id: 3 },
  { id: 4 },
  { id: 5 },
  { id: 6 },
  { id: 7 },
  { id: 8 },
  { id: 9 },
  { id: 10 },
]);

const selectedImageIds = ref<number[]>([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
const imageSelection = useIdSelection(selectedImageIds);

const selectedTotal = computed(
  () => selectedVideoIds.value.length + selectedImageIds.value.length,
);

const isValidationPassed = computed(() => {
  const hasVideos = selectedVideoIds.value.length > 0;
  const hasImages = selectedImageIds.value.length > 0;
  // Validation passes when only one type is selected (not both, not neither)
  // and within the maximum selectable limit
  const onlyOneType = (hasVideos && !hasImages) || (!hasVideos && hasImages);
  const withinLimit = selectedTotal.value <= maximumSelectable.value;
  return onlyOneType && withinLimit;
});

const handleSave = () => {
  isOpen.value = false;
};

const handleCancel = () => {
  isOpen.value = false;
};
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="865"
    closeButton
    useCustomClose
    @customClose="handleCancel"
    alignment="top"
  >
    <ModalHeader>
      {{
        $t("funnel-flow.paid-social.launchpad.incompatible-media-modal.title")
      }}
      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.incompatible-media-modal.description",
          )
        }}
      </template>

      <template #after>
        <Alert
          :type="isValidationPassed ? 'success' : 'warning'"
          class="tw:mt-6"
        >
          <span class="tw:flex tw:items-end tw:justify-between tw:gap-2">
            <span>
              <template v-if="isValidationPassed">
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.incompatible-media-modal.validation.passed",
                  )
                }}
              </template>
              <template v-else>
                <strong>
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.incompatible-media-modal.validation.action-required-prefix",
                    )
                  }}
                </strong>
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.incompatible-media-modal.validation.action-required-message",
                  )
                }}
              </template>
            </span>

            <strong>{{
              $t("funnel-flow.paid-social.launchpad.common.selection-count", {
                current: selectedTotal,
                max: maximumSelectable,
              })
            }}</strong>
          </span>
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <!-- Videos Section -->
      <div class="tw:grid tw:grid-cols-1 tw:gap-6">
        <AdsLaunchpadModalSection>
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.incompatible-media-modal.sections.videos",
              )
            }}
          </template>
          <template #actions>
            <Button
              type="button"
              variant="outlined"
              color="secondary"
              size="sm"
              @click="videoSelection.clear"
            >
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.incompatible-media-modal.sections.remove-all-videos",
                )
              }}
            </Button>
          </template>

          <!-- Videos -->
          <AdsLaunchpadModalVisualAssetGrid>
            <CardBase
              v-for="video in videos"
              :key="video.id"
              is="button"
              :color="
                videoSelection.isSelected(video.id) ? 'primary' : 'secondary'
              "
              hoverColor="primary"
              :shadow="false"
              class="tw:aspect-square"
              @click="videoSelection.toggle(video.id)"
            >
            </CardBase>
          </AdsLaunchpadModalVisualAssetGrid>
        </AdsLaunchpadModalSection>

        <!-- Images Section -->
        <AdsLaunchpadModalSection>
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.incompatible-media-modal.sections.images",
              )
            }}
          </template>
          <template #actions>
            <Button
              type="button"
              variant="outlined"
              color="secondary"
              size="sm"
              @click="imageSelection.clear"
            >
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.incompatible-media-modal.sections.remove-all-images",
                )
              }}
            </Button>
          </template>

          <!-- Images -->
          <AdsLaunchpadModalVisualAssetGrid>
            <CardBase
              v-for="image in images"
              :key="image.id"
              is="button"
              :color="
                imageSelection.isSelected(image.id) ? 'primary' : 'secondary'
              "
              hoverColor="primary"
              :shadow="false"
              class="tw:aspect-square"
              @click="imageSelection.toggle(image.id)"
            >
            </CardBase>
          </AdsLaunchpadModalVisualAssetGrid>
        </AdsLaunchpadModalSection>
      </div>
    </ModalBody>

    <ModalFooter>
      <Button
        type="button"
        variant="outlined"
        color="secondary"
        @click="handleCancel"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button type="button" :disabled="!isValidationPassed" @click="handleSave">
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
