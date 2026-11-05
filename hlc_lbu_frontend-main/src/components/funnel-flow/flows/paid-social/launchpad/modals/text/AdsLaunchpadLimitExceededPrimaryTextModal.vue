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
  () => initialCreative.value.bodies_max_amount,
);

const primaryTexts = computed(() =>
  initialCreative.value.bodies.map((body, index) => ({
    id: index,
    title: t(
      "funnel-flow.paid-social.launchpad.character-limit-modal.option-labels.primary-text-option",
      { n: index + 1 },
    ),
    text: body.text,
  })),
);

const selectedPrimaryTextIds = ref<number[]>([]);
const primaryTextSelection = useIdSelection(selectedPrimaryTextIds);

selectedPrimaryTextIds.value = preCheckStore.getSelectedBodies(
  props.creativeId,
);

const selectedTotal = computed(() => selectedPrimaryTextIds.value.length);

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

  await preCheckStore.setSelectedBodies(
    props.creativeId,
    selectedPrimaryTextIds.value,
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
              "funnel-flow.paid-social.launchpad.limit-primary-text-modal.title-standard",
            )
          : $t(
              "funnel-flow.paid-social.launchpad.limit-primary-text-modal.title",
            )
      }}

      <template #description>
        {{
          preCheckStore.isStandardMode
            ? $t(
                "funnel-flow.paid-social.launchpad.limit-primary-text-modal.description-standard",
              )
            : $t(
                "funnel-flow.paid-social.launchpad.limit-primary-text-modal.description",
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
                    "funnel-flow.paid-social.launchpad.limit-primary-text-modal.validation.passed",
                  )
                }}
              </template>
              <template v-else>
                <strong>
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.limit-primary-text-modal.validation.action-required-prefix",
                    )
                  }}
                </strong>
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.limit-primary-text-modal.validation.action-required-message",
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
          v-for="primaryText in primaryTexts"
          :key="primaryText.id"
          :selected="primaryTextSelection.isSelected(primaryText.id)"
          clamp
          :readonly="readonly"
          @click="!readonly && primaryTextSelection.toggle(primaryText.id)"
        >
          <template #title>
            {{ primaryText.title }}
          </template>

          {{ primaryText.text }}
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
