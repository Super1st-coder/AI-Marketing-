<script setup lang="ts">
import type {
  AdsExperimentByAdSetData,
  AdsExperimentCategory,
  AdsExperimentSubcategory,
  AdsExperimentType,
} from "@/services/funnel-flow/paid-social/AdsExperiment";
import Modal from "@/components/modals/base/Modal.vue";
import AdsExperiment from "@/services/funnel-flow/paid-social/AdsExperiment";

export interface CreativeAngleState {
  format?: AdsExperimentType;
  primaryDriver?: AdsExperimentCategory;
  visualExecution?: AdsExperimentSubcategory;
}

const props = defineProps<{
  experiment?: AdsExperimentByAdSetData | undefined;
}>();

const isOpen = defineModel<boolean>({ required: true });

const modalRef = ref<InstanceType<typeof Modal>>();

// Current step: 1 or 2
const currentStep = ref<1 | 2>(1);

// State that accumulates across all steps. Every new creative angle is static
const state = reactive<CreativeAngleState>({
  format: "static",
  primaryDriver: undefined,
  visualExecution: undefined,
});

const brandId = useBrandId();

// Reset scroll on step change
watch(currentStep, () => {
  modalRef.value?.resetScroll();
});

// Initialize state when modal opens with experiment data (edit mode)
watch(isOpen, async (open) => {
  if (open && props.experiment) {
    // Pre-fill format. An existing one keeps its own, since its primary
    // driver and visual execution belong to it
    state.format = props.experiment.type;

    // Fetch and pre-fill primary driver (category)
    if (props.experiment.subcategory?.category?.id) {
      const categoriesResponse = await AdsExperiment.getExperimentCategories(
        brandId,
        props.experiment.type,
      );
      state.primaryDriver = categoriesResponse.data.find(
        (cat) => cat.id === props.experiment?.subcategory?.category?.id,
      );

      // Fetch and pre-fill visual execution (subcategory)
      if (state.primaryDriver && props.experiment.subcategory?.id) {
        const subcategoriesResponse =
          await AdsExperiment.getExperimentSubcategories(
            brandId,
            state.primaryDriver.id,
          );
        state.visualExecution = subcategoriesResponse.data.subcategories.find(
          (sub) => sub.id === props.experiment?.subcategory?.id,
        );
      }
    }
  } else if (!open) {
    // Reset everything when modal closes
    currentStep.value = 1;
    state.format = "static";
    state.primaryDriver = undefined;
    state.visualExecution = undefined;
  }
});

// Step 1: Primary driver selection (just updates state, doesn't navigate)
function handlePrimaryDriverSelect(primaryDriver: AdsExperimentCategory) {
  // Reset visual execution if the primary driver is changed
  if (state.primaryDriver && state.primaryDriver.id !== primaryDriver.id) {
    state.visualExecution = undefined;
  }

  state.primaryDriver = primaryDriver;
}

// Step 1: Navigate to step 2
function handleStep1Next() {
  if (state.primaryDriver) {
    currentStep.value = 2;
  }
}

// Step 1: Cancel
function handleStep1Cancel() {
  isOpen.value = false;
}

// Step 2: Visual execution selection
function handleVisualExecutionSelect(
  visualExecution: AdsExperimentSubcategory,
) {
  state.visualExecution = visualExecution;
}

// Step 2: Handle primary driver update (when subcategories are added)
function handlePrimaryDriverUpdated(updatedDriver: AdsExperimentCategory) {
  state.primaryDriver = updatedDriver;
}

// Step 2: Confirm and close
function handleStep2Confirm() {
  if (state.visualExecution) {
    isOpen.value = false;
  }
}

// Step 2: Go back to step 1
function handleStep2Back() {
  currentStep.value = 1;
}
</script>

<template>
  <Modal ref="modalRef" v-model="isOpen" :maxWidth="700" closeButton>
    <Suspense timeout="0">
      <!-- Step 1: Primary Driver -->
      <CreativeAnglePrimaryDriver
        v-if="currentStep === 1"
        :format="state.format"
        :selectedDriver="state.primaryDriver"
        @select="handlePrimaryDriverSelect"
        @next="handleStep1Next"
        @cancel="handleStep1Cancel"
      />

      <!-- Step 2: Visual Execution -->
      <CreativeAngleVisualExecution
        v-else-if="currentStep === 2"
        :format="state.format"
        :primaryDriver="state.primaryDriver"
        :selectedExecution="state.visualExecution"
        :experiment="props.experiment"
        @select="handleVisualExecutionSelect"
        @confirm="handleStep2Confirm"
        @back="handleStep2Back"
        @primaryDriverUpdated="handlePrimaryDriverUpdated"
      />

      <template #fallback>
        <CircleLoaderDefault class="tw:grow tw:py-32" />
      </template>
    </Suspense>
  </Modal>
</template>
