<script setup lang="ts">
import { LaunchPreCheckTextItem } from "@/services/funnel-flow/ChannelConnections";
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

const getTexts = (
  initialTexts: LaunchPreCheckTextItem[],
  selectedIds: number[],
  getTitle: (index: number) => string,
) => {
  // Map first to not lose the original index
  let mapped = initialTexts.map((body, index) => ({
    id: index,
    title: getTitle(index),
    text: body.text,
  }));

  // Filter out selected texts
  mapped = mapped.filter((text) => selectedIds.some((id) => id === text.id));

  // Filter out duplicated texts from the remaining texts
  mapped = mapped.filter((text, index) => {
    // Find out if the text has duplicates by checking all items
    const hasDuplicates = mapped.some(
      (t) => t.text === text.text && t.id !== text.id,
    );

    if (!hasDuplicates) {
      return false;
    }

    // Only include in the list the duplicates that aren't the first of their kind:
    // if there are three texts: "Foo", "Foo", "Foo". Then, only two "Foo" will be
    // displayed as duplicates.
    const firstIndexOfDuplicated = mapped.findIndex(
      (t) => t.text === text.text,
    );
    return index !== firstIndexOfDuplicated;
  });

  return mapped;
};

const duplicatedBodies = getTexts(
  initialCreative.value.bodies,
  preCheckStore.getSelectedBodies(props.creativeId),
  (index) =>
    t(
      "funnel-flow.paid-social.launchpad.character-limit-modal.option-labels.primary-text-option",
      { n: index + 1 },
    ),
);

const duplicatedHeadlines = getTexts(
  initialCreative.value.titles,
  preCheckStore.getSelectedTitles(props.creativeId),
  (index) =>
    t(
      "funnel-flow.paid-social.launchpad.character-limit-modal.option-labels.headline-option",
      { n: index + 1 },
    ),
);
const duplicatedDescriptions = getTexts(
  initialCreative.value.descriptions,
  preCheckStore.getSelectedDescriptions(props.creativeId),
  (index) =>
    t(
      "funnel-flow.paid-social.launchpad.character-limit-modal.option-labels.description-option",
      { n: index + 1 },
    ),
);

const selectedBodyIds = ref<number[]>([]);
const selectedHeadlineIds = ref<number[]>([]);
const selectedDescriptionIds = ref<number[]>([]);

const bodiesSelection = useIdSelection(selectedBodyIds);
const headlinesSelection = useIdSelection(selectedHeadlineIds);
const descriptionsSelection = useIdSelection(selectedDescriptionIds);

const getSelectedIds = (items: { id: number }[], selected: number[]) => {
  return items.filter((b) => selected.includes(b.id)).map((b) => b.id);
};

selectedBodyIds.value = getSelectedIds(
  duplicatedBodies,
  preCheckStore.getSelectedBodies(props.creativeId),
);
selectedHeadlineIds.value = getSelectedIds(
  duplicatedHeadlines,
  preCheckStore.getSelectedTitles(props.creativeId),
);
selectedDescriptionIds.value = getSelectedIds(
  duplicatedDescriptions,
  preCheckStore.getSelectedDescriptions(props.creativeId),
);

const isValidationPassed = computed(
  () =>
    selectedBodyIds.value.length === 0 &&
    selectedHeadlineIds.value.length === 0 &&
    selectedDescriptionIds.value.length === 0,
);

const isSaving = ref(false);

const handleSave = async () => {
  isSaving.value = true;

  const creativeId = props.creativeId;

  // Indices that are not shown in the modal
  const bodyIdsInModal = duplicatedBodies.map((b) => b.id);
  const headlineIdsInModal = duplicatedHeadlines.map((h) => h.id);
  const descriptionIdsInModal = duplicatedDescriptions.map((d) => d.id);

  // Set new selected indices in the store
  await preCheckStore.setSelectedTextIndices(creativeId, {
    bodies: [
      ...preCheckStore
        .getSelectedBodies(creativeId)
        .filter((id) => !bodyIdsInModal.includes(id)),
      ...selectedBodyIds.value,
    ],
    titles: [
      ...preCheckStore
        .getSelectedTitles(creativeId)
        .filter((id) => !headlineIdsInModal.includes(id)),
      ...selectedHeadlineIds.value,
    ],
    descriptions: [
      ...preCheckStore
        .getSelectedDescriptions(creativeId)
        .filter((id) => !descriptionIdsInModal.includes(id)),
      ...selectedDescriptionIds.value,
    ],
  });

  isOpen.value = false;
  isSaving.value = false;
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
      {{ $t("funnel-flow.paid-social.launchpad.duplicate-modal.title") }}

      <template #description>
        {{
          $t("funnel-flow.paid-social.launchpad.duplicate-modal.description")
        }}
      </template>

      <template #after>
        <Alert
          :type="isValidationPassed ? 'success' : 'warning'"
          class="tw:mt-6"
        >
          <template v-if="isValidationPassed">
            {{
              $t(
                "funnel-flow.paid-social.launchpad.duplicate-modal.validation.passed",
              )
            }}
          </template>
          <template v-else>
            <strong>
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.duplicate-modal.validation.action-required-prefix",
                )
              }}
            </strong>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.duplicate-modal.validation.action-required-message",
              )
            }}
          </template>
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <div class="tw:grid tw:grid-cols-1 tw:gap-6">
        <AdsLaunchpadModalSection v-if="duplicatedBodies.length > 0">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.character-limit-modal.sections.primary-text",
              )
            }}
          </template>
          <template #actions>
            <Button
              v-if="!readonly"
              type="button"
              variant="outlined"
              color="secondary"
              size="sm"
              @click="bodiesSelection.clear"
            >
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.duplicate-modal.sections.remove-all-duplicates",
                )
              }}
            </Button>
          </template>
          <AdsLaunchpadModalVisualAssetGrid :columns="3">
            <AdsLaunchpadModalTextCard
              v-for="item in duplicatedBodies"
              :key="item.id"
              :selected="bodiesSelection.isSelected(item.id)"
              clamp
              :readonly="readonly"
              @click="!readonly && bodiesSelection.toggle(item.id)"
            >
              <template #title>{{ item.title }}</template>
              {{ item.text }}
            </AdsLaunchpadModalTextCard>
          </AdsLaunchpadModalVisualAssetGrid>
        </AdsLaunchpadModalSection>

        <AdsLaunchpadModalSection v-if="duplicatedHeadlines.length > 0">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.character-limit-modal.sections.headlines",
              )
            }}
          </template>
          <template #actions>
            <Button
              v-if="!readonly"
              type="button"
              variant="outlined"
              color="secondary"
              size="sm"
              @click="headlinesSelection.clear"
            >
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.duplicate-modal.sections.remove-all-duplicates",
                )
              }}
            </Button>
          </template>
          <AdsLaunchpadModalVisualAssetGrid :columns="3">
            <AdsLaunchpadModalTextCard
              v-for="headline in duplicatedHeadlines"
              :key="headline.id"
              :selected="headlinesSelection.isSelected(headline.id)"
              clamp
              :readonly="readonly"
              @click="!readonly && headlinesSelection.toggle(headline.id)"
            >
              <template #title>{{ headline.title }}</template>
              {{ headline.text }}
            </AdsLaunchpadModalTextCard>
          </AdsLaunchpadModalVisualAssetGrid>
        </AdsLaunchpadModalSection>

        <AdsLaunchpadModalSection v-if="duplicatedDescriptions.length > 0">
          <template #title>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.character-limit-modal.sections.descriptions",
              )
            }}
          </template>
          <template #actions>
            <Button
              v-if="!readonly"
              type="button"
              variant="outlined"
              color="secondary"
              size="sm"
              @click="descriptionsSelection.clear"
            >
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.duplicate-modal.sections.remove-all-duplicates",
                )
              }}
            </Button>
          </template>
          <AdsLaunchpadModalVisualAssetGrid :columns="3">
            <AdsLaunchpadModalTextCard
              v-for="item in duplicatedDescriptions"
              :key="item.id"
              :selected="descriptionsSelection.isSelected(item.id)"
              clamp
              :readonly="readonly"
              @click="!readonly && descriptionsSelection.toggle(item.id)"
            >
              <template #title>{{ item.title }}</template>
              {{ item.text }}
            </AdsLaunchpadModalTextCard>
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
