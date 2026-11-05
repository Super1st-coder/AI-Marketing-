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

const maximumSelectable = computed(
  () => initialCreative.value.images_max_amount,
);

const images = computed(() =>
  initialCreative.value.images.map((image, index) => ({
    id: index,
    url: image.url,
    valid: image.valid,
    error: image.error,
  })),
);

const selectedImageIds = ref<number[]>([]);
const imageSelection = useIdSelection(selectedImageIds);

selectedImageIds.value = preCheckStore.getSelectedImages(props.creativeId);

const selectedTotal = computed(() => selectedImageIds.value.length);

const excessCount = computed(() => {
  return Math.max(0, selectedTotal.value - maximumSelectable.value);
});

const isValidationPassed = computed(() => {
  return (
    selectedTotal.value >= 1 && selectedTotal.value <= maximumSelectable.value
  );
});

const isSaving = ref(false);

async function handleSave() {
  isSaving.value = true;

  await preCheckStore.setSelectedImages(
    props.creativeId,
    selectedImageIds.value,
  );

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
        preCheckStore.isStandardMode
          ? $t(
              "funnel-flow.paid-social.launchpad.image-limit-modal.title-standard",
            )
          : $t("funnel-flow.paid-social.launchpad.image-limit-modal.title")
      }}

      <template #description>
        {{
          preCheckStore.isStandardMode
            ? $t(
                "funnel-flow.paid-social.launchpad.image-limit-modal.description-standard",
                { max: maximumSelectable },
              )
            : $t(
                "funnel-flow.paid-social.launchpad.image-limit-modal.description",
                { max: maximumSelectable },
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
                    "funnel-flow.paid-social.launchpad.image-limit-modal.validation.passed",
                  )
                }}
              </template>
              <template v-else>
                <strong>
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.image-limit-modal.validation.action-required-prefix",
                    )
                  }}
                </strong>
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.image-limit-modal.validation.action-required-message",
                    { count: excessCount },
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
      <AdsLaunchpadModalVisualAssetGrid :columns="5">
        <CardBase
          v-for="image in images"
          :key="image.id"
          :is="readonly ? 'div' : 'button'"
          :outlineColor="
            imageSelection.isSelected(image.id) ? 'primary' : 'default'
          "
          :hoverColor="readonly ? undefined : 'primary'"
          :shadow="false"
          :borderWidth="2"
          @click="!readonly && imageSelection.toggle(image.id)"
          class="tw:aspect-square tw:overflow-hidden"
        >
          <img :src="image.url" class="tw:h-full tw:w-full tw:object-contain" />
        </CardBase>
      </AdsLaunchpadModalVisualAssetGrid>
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
