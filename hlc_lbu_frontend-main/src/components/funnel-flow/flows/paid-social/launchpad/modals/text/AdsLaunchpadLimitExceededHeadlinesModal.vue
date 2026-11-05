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
  () => initialCreative.value.titles_max_amount,
);

const headlines = computed(() =>
  initialCreative.value.titles.map((title, index) => ({
    id: index,
    title: t(
      "funnel-flow.paid-social.launchpad.character-limit-modal.option-labels.headline-option",
      { n: index + 1 },
    ),
    text: title.text,
  })),
);

const selectedHeadlineIds = ref<number[]>([]);
const headlineSelection = useIdSelection(selectedHeadlineIds);

selectedHeadlineIds.value = preCheckStore.getSelectedTitles(props.creativeId);

const selectedTotal = computed(() => selectedHeadlineIds.value.length);

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

  await preCheckStore.setSelectedTitles(
    props.creativeId,
    selectedHeadlineIds.value,
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
              "funnel-flow.paid-social.launchpad.limit-headlines-modal.title-standard",
            )
          : $t("funnel-flow.paid-social.launchpad.limit-headlines-modal.title")
      }}

      <template #description>
        {{
          preCheckStore.isStandardMode
            ? $t(
                "funnel-flow.paid-social.launchpad.limit-headlines-modal.description-standard",
              )
            : $t(
                "funnel-flow.paid-social.launchpad.limit-headlines-modal.description",
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
                    "funnel-flow.paid-social.launchpad.limit-headlines-modal.validation.passed",
                  )
                }}
              </template>
              <template v-else>
                <strong>
                  {{
                    $t(
                      "funnel-flow.paid-social.launchpad.limit-headlines-modal.validation.action-required-prefix",
                    )
                  }}
                </strong>
                {{
                  $t(
                    "funnel-flow.paid-social.launchpad.limit-headlines-modal.validation.action-required-message",
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
          v-for="headline in headlines"
          :key="headline.id"
          :selected="headlineSelection.isSelected(headline.id)"
          clamp
          :readonly="readonly"
          @click="!readonly && headlineSelection.toggle(headline.id)"
        >
          <template #title>
            {{ headline.title }}
          </template>

          {{ headline.text }}
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
