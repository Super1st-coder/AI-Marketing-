<script setup lang="ts">
const props = defineProps<{
  creativeId: number;
  // The summary shows the checks without allowing changes
  readonly?: boolean;
}>();

const isOpen = defineModel<boolean>({ required: true });
const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

const initialCreative = computed(() =>
  preCheckStore.getInitialCreative(props.creativeId)!,
);

const invalidImages = computed(() =>
  initialCreative.value.images
    .map((image, index) => ({
      id: index,
      url: image.url,
      error: image.error,
      valid: image.valid,
    }))
    .filter((item) => !item.valid),
);

const getSelectedIds = (items: { id: number }[], selected: number[]) =>
  items.filter((item) => selected.includes(item.id)).map((item) => item.id);

const selectedInvalidImageIds = ref<number[]>([]);
const imageSelection = useIdSelection(selectedInvalidImageIds);

selectedInvalidImageIds.value = getSelectedIds(
  invalidImages.value,
  preCheckStore.getSelectedImages(props.creativeId),
);

const selectedCount = computed(() => selectedInvalidImageIds.value.length);

const isValidationPassed = computed(
  () => selectedInvalidImageIds.value.length === 0,
);

function clearAllInvalid() {
  imageSelection.clear();
}

const isSaving = ref(false);

async function handleSave() {
  isSaving.value = true;

  const creativeId = props.creativeId;

  const invalidIdsInModal = invalidImages.value.map((img) => img.id);

  // Remove all invalid from current selection, then add back only the ones still selected in modal
  const newSelectedImages = [
    ...preCheckStore
      .getSelectedImages(creativeId)
      .filter((id) => !invalidIdsInModal.includes(id)),
    ...selectedInvalidImageIds.value,
  ];

  await preCheckStore.setSelectedImages(creativeId, newSelectedImages);

  isOpen.value = false;
  isSaving.value = false;
}

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
        $t("funnel-flow.paid-social.launchpad.invalid-media-specs-modal.title")
      }}

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.invalid-media-specs-modal.description",
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
                    "funnel-flow.paid-social.launchpad.invalid-media-specs-modal.validation.passed",
                  )
                }}
              </template>
              <template v-else>
                <strong>
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.invalid-media-specs-modal.validation.action-required-prefix",
                    )
                  }}
                </strong>
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.invalid-media-specs-modal.validation.action-required-message",
                    { count: selectedCount },
                  )
                }}
              </template>
            </span>
          </span>
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <div class="tw:grid tw:grid-cols-1 tw:gap-6">
        <AdsLaunchpadModalSection v-if="invalidImages.length > 0">
          <template #title>
            {{ $t("funnel-flow.paid-social.summary.sets.ads.title") }}
          </template>
          <template #actions>
            <Button
              v-if="!readonly"
              type="button"
              variant="outlined"
              color="secondary"
              size="sm"
              @click="clearAllInvalid"
            >
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.invalid-media-specs-modal.actions.clear-all-invalid",
                )
              }}
            </Button>
          </template>

          <AdsLaunchpadModalVisualAssetGrid :columns="4">
            <CardBase
              v-for="image in invalidImages"
              :key="image.id"
              :is="readonly ? 'div' : 'button'"
              :outlineColor="
                imageSelection.isSelected(image.id) ? 'primary' : 'default'
              "
              :hoverColor="readonly ? undefined : 'primary'"
              :shadow="false"
              :borderWidth="2"
              class="tw:aspect-square tw:p-3"
              @click="!readonly && imageSelection.toggle(image.id)"
            >
              <h3 class="tw:mb-2.5 tw:text-sm tw:font-semibold">
                {{ initialCreative.name }}
              </h3>

              <img
                :src="image.url"
                class="tw:mb-2.5 tw:aspect-square tw:overflow-hidden tw:rounded-xl tw:bg-gray-400 tw:object-contain"
              />

              <Chip color="warning" variant="label">
                {{ image.error }}
              </Chip>
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
        {{ $t("global.close") }}
      </Button>

      <Button
        v-if="!readonly"
        type="button"
        :disabled="!isValidationPassed"
        :isLoading="isSaving"
        @click="handleSave"
      >
        {{ $t("global.save") }}
      </Button>
    </ModalFooter>
  </Modal>
</template>
