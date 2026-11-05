<script setup lang="ts">
const { t } = useI18n();
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
  () => initialCreative.value.descriptions_max_amount,
);

const descriptions = computed(() =>
  initialCreative.value.descriptions.map((desc, index) => ({
    id: index,
    title: t(
      "funnel-flow.paid-social.launchpad.character-limit-modal.option-labels.description-option",
      { n: index + 1 },
    ),
    text: desc.text,
  })),
);

const selectedDescriptionIds = ref<number[]>([]);
const descriptionSelection = useIdSelection(selectedDescriptionIds);

selectedDescriptionIds.value = preCheckStore.getSelectedDescriptions(
  props.creativeId,
);

const selectedTotal = computed(() => selectedDescriptionIds.value.length);

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

  await preCheckStore.setSelectedDescriptions(
    props.creativeId,
    selectedDescriptionIds.value,
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
              "funnel-flow.paid-social.launchpad.limit-description-modal.title-standard",
            )
          : $t(
              "funnel-flow.paid-social.launchpad.limit-description-modal.title",
            )
      }}

      <template #description>
        {{
          preCheckStore.isStandardMode
            ? $t(
                "funnel-flow.paid-social.launchpad.limit-description-modal.description-standard",
              )
            : $t(
                "funnel-flow.paid-social.launchpad.limit-description-modal.description",
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
                    "funnel-flow.paid-social.launchpad.limit-description-modal.validation.passed",
                  )
                }}
              </template>
              <template v-else>
                <strong>
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.limit-description-modal.validation.action-required-prefix",
                    )
                  }}
                </strong>
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.limit-description-modal.validation.action-required-message",
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
      <AdsLaunchpadModalVisualAssetGrid :columns="3">
        <AdsLaunchpadModalTextCard
          v-for="description in descriptions"
          :key="description.id"
          :selected="descriptionSelection.isSelected(description.id)"
          clamp
          :readonly="readonly"
          @click="!readonly && descriptionSelection.toggle(description.id)"
        >
          <template #title>
            {{ description.title }}
          </template>

          {{ description.text }}
        </AdsLaunchpadModalTextCard>
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
