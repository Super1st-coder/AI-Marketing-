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

const currentCreative = computed(() =>
  preCheckStore.creativesWithData.find((c) => c.idx === props.creativeId)!,
);

const getTexts = (
  initialTexts: LaunchPreCheckTextItem[],
  selectedIndices: number[],
  getTitle: (index: number) => string,
) => {
  return selectedIndices
    .map((initialIndex, i) => ({
      id: initialIndex,
      title: getTitle(initialIndex),
      text: initialTexts[i].text,
      validLength: initialTexts[i].valid_length,
    }))
    .filter((item) => !item.validLength);
};

const invalidBodies = getTexts(
  currentCreative.value.bodies,
  preCheckStore.getSelectedBodies(props.creativeId),
  (index) =>
    t(
      "funnel-flow.paid-social.launchpad.character-limit-modal.option-labels.primary-text-option",
      { n: index + 1 },
    ),
);

const invalidHeadlines = getTexts(
  currentCreative.value.titles,
  preCheckStore.getSelectedTitles(props.creativeId),
  (index) =>
    t(
      "funnel-flow.paid-social.launchpad.character-limit-modal.option-labels.headline-option",
      { n: index + 1 },
    ),
);

const invalidDescriptions = getTexts(
  currentCreative.value.descriptions,
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
  invalidBodies,
  preCheckStore.getSelectedBodies(props.creativeId),
);
selectedHeadlineIds.value = getSelectedIds(
  invalidHeadlines,
  preCheckStore.getSelectedTitles(props.creativeId),
);
selectedDescriptionIds.value = getSelectedIds(
  invalidDescriptions,
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

  const bodyIdsInModal = invalidBodies.map((b) => b.id);
  const headlineIdsInModal = invalidHeadlines.map((h) => h.id);
  const descriptionIdsInModal = invalidDescriptions.map((d) => d.id);

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
      {{ $t("funnel-flow.paid-social.launchpad.character-limit-modal.title") }}

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.character-limit-modal.description",
          )
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
                "funnel-flow.paid-social.launchpad.character-limit-modal.validation.passed",
              )
            }}
          </template>
          <template v-else>
            <strong>
              {{
                $t(
                  "funnel-flow.paid-social.launchpad.character-limit-modal.validation.action-required-prefix",
                )
              }}
            </strong>
            {{
              $t(
                "funnel-flow.paid-social.launchpad.character-limit-modal.validation.action-required-message",
              )
            }}
          </template>
        </Alert>
      </template>
    </ModalHeader>

    <ModalBody>
      <div class="tw:grid tw:grid-cols-1 tw:gap-6">
        <AdsLaunchpadModalSection v-if="invalidBodies.length > 0">
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
                  "funnel-flow.paid-social.launchpad.character-limit-modal.sections.remove-all-invalid",
                )
              }}
            </Button>
          </template>
          <AdsLaunchpadModalVisualAssetGrid :columns="3">
            <AdsLaunchpadModalTextCard
              v-for="item in invalidBodies"
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

        <AdsLaunchpadModalSection v-if="invalidHeadlines.length > 0">
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
                  "funnel-flow.paid-social.launchpad.character-limit-modal.sections.remove-all-invalid",
                )
              }}
            </Button>
          </template>
          <AdsLaunchpadModalVisualAssetGrid :columns="3">
            <AdsLaunchpadModalTextCard
              v-for="headline in invalidHeadlines"
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

        <AdsLaunchpadModalSection v-if="invalidDescriptions.length > 0">
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
                  "funnel-flow.paid-social.launchpad.character-limit-modal.sections.remove-all-invalid",
                )
              }}
            </Button>
          </template>
          <AdsLaunchpadModalVisualAssetGrid :columns="3">
            <AdsLaunchpadModalTextCard
              v-for="item in invalidDescriptions"
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
