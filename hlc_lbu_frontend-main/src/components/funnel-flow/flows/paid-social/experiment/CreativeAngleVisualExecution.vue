<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import type {
  AdsExperimentByAdSetData,
  AdsExperimentCategory,
  AdsExperimentSubcategory,
  AdsExperimentType,
} from "@/services/funnel-flow/paid-social/AdsExperiment";
import AdsExperiment from "@/services/funnel-flow/paid-social/AdsExperiment";

const props = defineProps<{
  format?: AdsExperimentType;
  primaryDriver?: AdsExperimentCategory;
  selectedExecution?: AdsExperimentSubcategory;
  experiment?: AdsExperimentByAdSetData | undefined;
}>();

const emit = defineEmits<{
  select: [execution: AdsExperimentSubcategory];
  confirm: [];
  back: [];
  primaryDriverUpdated: [driver: AdsExperimentCategory];
}>();

// A little wait
await sleep(1000);

// State
const brandId = useBrandId();
const store = useFunnelPaidSocialExperimentStore();
const formStore = useFunnelPaidSocialFormStore();
const selectedExecution = ref<AdsExperimentSubcategory | undefined>(
  props.selectedExecution,
);
const isSubmitting = ref(false);
const isAddSubcategoryModalOpen = ref(false);

const isEditing = computed(() => !!props.experiment?.id);

// Modal state for experiment change confirmation
const showChangeModal = ref(false);
const pendingConfirmData = ref<
  | {
      subcategoryId: number;
      type: AdsExperimentType;
    }
  | undefined
>(undefined);

watch(
  () => props.selectedExecution,
  (newValue) => {
    selectedExecution.value = newValue;
  },
);

async function handleSubcategoryCreated(createdName: string) {
  if (!props.primaryDriver?.id) return;

  // Refetch subcategories to get the updated list
  const response = await AdsExperiment.getExperimentSubcategories(
    brandId,
    props.primaryDriver.id,
  );

  // Update the primaryDriver prop by emitting an event to parent
  const updatedPrimaryDriver: AdsExperimentCategory = {
    ...props.primaryDriver,
    subcategories: response.data.subcategories,
  };
  emit("primaryDriverUpdated", updatedPrimaryDriver);

  // Find and select the newly created subcategory by name
  const newSubcategory = response.data.subcategories.find(
    (sub) => sub.name === createdName,
  );
  if (newSubcategory) {
    handleSelect(newSubcategory);
  }
}

function handleSelect(execution: AdsExperimentSubcategory) {
  selectedExecution.value = execution;
  emit("select", execution);
}

async function handleConfirm() {
  isSubmitting.value = true;

  if (!selectedExecution.value?.id || !props.format) {
    isSubmitting.value = false;
    throw new UnidentifiedError();
  }

  // Check if the selected subcategory is different from the current one
  const hasSubcategoryChanged =
    selectedExecution.value.id !== props.experiment?.subcategory?.id;

  // Check if ad set has filled ads
  const hasFilledAds = formStore.adSetHasFilledAds(store.selectedAdSet.id);

  if (isEditing.value && hasSubcategoryChanged && hasFilledAds) {
    // Show confirm change modal
    pendingConfirmData.value = {
      subcategoryId: selectedExecution.value.id,
      type: props.format,
    };
    showChangeModal.value = true;
    isSubmitting.value = false;
  } else {
    // Otherwise, save directly
    await store.defineCurrentExperiment(
      selectedExecution.value.id,
      props.format,
    );
    isSubmitting.value = false;
    emit("confirm");
  }
}

async function handleConfirmChange() {
  if (!pendingConfirmData.value) return;

  isSubmitting.value = true;

  await store.defineCurrentExperiment(
    pendingConfirmData.value.subcategoryId,
    pendingConfirmData.value.type,
  );

  pendingConfirmData.value = undefined;
  showChangeModal.value = false;
  isSubmitting.value = false;

  emit("confirm");
}

function handleBack() {
  emit("back");
}
</script>

<template>
  <div>
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.creative-angle.visual-execution.title") }}
    </ModalHeader>

    <Separator />

    <div class="tw:px-6 tw:py-6">
      <h3 class="tw:text-xl tw:font-bold">
        {{
          `${$t(`funnel-flow.paid-social.creative-angle.formats.${props.format}.title`)} | ${
            props.primaryDriver?.name &&
            $te(
              `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(props.primaryDriver.name)}.name`,
            )
              ? $t(
                  `funnel-flow.paid-social.creative-angle.categories.${toI18nKeySegment(props.primaryDriver.name)}.name`,
                )
              : props.primaryDriver?.name
          }`
        }}
      </h3>
    </div>

    <Separator />

    <ModalBody class="tw:pt-6">
      <!-- Visual execution options -->
      <div
        v-if="
          primaryDriver?.subcategories && primaryDriver.subcategories.length > 0
        "
        class="tw:flex tw:flex-col tw:gap-4"
      >
        <CreativeAngleVisualExecutionCard
          v-for="execution in primaryDriver.subcategories"
          :execution="execution"
          :isSelected="selectedExecution?.id === execution.id"
          @click="handleSelect(execution)"
        />
      </div>
      <div v-else class="tw:py-8 tw:text-center">
        <p class="tw:text-secondary-text">
          {{
            $t(
              "funnel-flow.paid-social.creative-angle.visual-execution.empty-state",
            )
          }}
        </p>
      </div>
    </ModalBody>

    <ModalFooter>
      <template #before>
        <Button
          type="button"
          variant="text"
          leftIcon="tabler-plus"
          class="tw:px-0!"
          @click="isAddSubcategoryModalOpen = true"
          :disabled="!primaryDriver?.id"
        >
          {{
            $t(
              "funnel-flow.paid-social.creative-angle.visual-execution.add-custom-variable",
            )
          }}
        </Button>
      </template>

      <Button
        color="secondary"
        variant="outlined"
        @click="handleBack"
        type="button"
        leftIcon="tabler-arrow-left"
        :disabled="isSubmitting"
      >
        {{ $t("global.back") }}
      </Button>

      <Button
        @click="handleConfirm"
        type="button"
        :disabled="!selectedExecution"
        :isLoading="isSubmitting"
      >
        {{
          $t(
            "funnel-flow.paid-social.creative-angle.visual-execution.confirm-selection",
          )
        }}
      </Button>
    </ModalFooter>

    <!-- Add subcategory modal -->
    <CreativeAngleAddSubcategoryModal
      v-if="primaryDriver?.id"
      v-model="isAddSubcategoryModalOpen"
      :categoryId="primaryDriver.id"
      @subcategoryCreated="handleSubcategoryCreated"
    />

    <!-- Change Modal -->
    <CreativeAngleChangeModal
      v-model="showChangeModal"
      :adSetId="store.selectedAdSet.id"
      :channelId="store.channelGroupId"
      @keepExisting="handleConfirmChange"
      @deleteAds="handleConfirmChange"
    />
  </div>
</template>
