<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import type {
  AdsExperimentCategory,
  AdsExperimentCreateCategoryData,
  AdsExperimentType,
} from "@/services/funnel-flow/paid-social/AdsExperiment";
import AdsExperiment from "@/services/funnel-flow/paid-social/AdsExperiment";

const props = defineProps<{
  format?: AdsExperimentType;
  selectedDriver?: AdsExperimentCategory;
}>();

const emit = defineEmits<{
  select: [driver: AdsExperimentCategory];
  next: [];
  cancel: [];
}>();

if (!props.format) {
  throw new UnidentifiedError();
}

const brandId = useBrandId();

// Fetch categories - make it reactive
const categories = ref<AdsExperimentCategory[]>([]);

async function fetchCategories() {
  const response = await AdsExperiment.getExperimentCategories(
    brandId,
    props.format!,
  );
  categories.value = response.data;
}

// Initial fetch
await fetchCategories();

// State
const selectedDriver = ref<AdsExperimentCategory | undefined>(
  props.selectedDriver,
);
const isAddCategoryModalOpen = ref(false);

watch(
  () => props.selectedDriver,
  (newValue) => {
    selectedDriver.value = newValue;
  },
);

function handleSelect(driver: AdsExperimentCategory) {
  selectedDriver.value = driver;
  emit("select", driver);
}

function handleNext() {
  if (selectedDriver.value) {
    emit("next");
  }
}

function handleCancel() {
  emit("cancel");
}

async function handleCategoryCreated(
  newCategory: AdsExperimentCreateCategoryData,
) {
  // Refetch categories to get the updated list
  await fetchCategories();

  // Find and select the newly created category from the refetched list
  const createdCategory = categories.value.find(
    (cat) => cat.id === newCategory.id,
  );
  if (createdCategory) {
    handleSelect(createdCategory);
  }
}
</script>

<template>
  <div>
    <ModalHeader>
      {{ $t("funnel-flow.paid-social.creative-angle.primary-driver.title") }}
    </ModalHeader>

    <ModalBody>
      <div v-if="categories.length > 0" class="tw:flex tw:flex-col tw:gap-6">
        <CreativeAnglePrimaryDriverCard
          v-for="driver in categories"
          :driver="driver"
          :isSelected="selectedDriver?.id === driver.id"
          @click="handleSelect(driver)"
        />
      </div>
      <div v-else class="tw:py-8 tw:text-center">
        <p class="tw:text-secondary-text">
          {{
            $t(
              "funnel-flow.paid-social.creative-angle.primary-driver.empty-state",
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
          @click="isAddCategoryModalOpen = true"
        >
          {{
            $t(
              "funnel-flow.paid-social.creative-angle.primary-driver.add-new-category",
            )
          }}
        </Button>
      </template>

      <Button
        color="secondary"
        variant="outlined"
        @click="handleCancel"
        type="button"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button
        @click="handleNext"
        type="button"
        :disabled="!selectedDriver"
        icon="tabler-arrow-right"
      >
        {{
          $t("funnel-flow.paid-social.creative-angle.primary-driver.next-step")
        }}
      </Button>
    </ModalFooter>

    <CreativeAngleAddCategoryModal
      v-model="isAddCategoryModalOpen"
      :format="format!"
      @categoryCreated="handleCategoryCreated"
    />
  </div>
</template>
