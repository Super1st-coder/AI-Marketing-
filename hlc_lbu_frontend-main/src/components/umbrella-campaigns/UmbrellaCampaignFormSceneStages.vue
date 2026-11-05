<script setup lang="ts">
import { UmbrellaCampaignData } from "@/services/projects/UmbrellaCampaignsApi";
import UmbrellaCampaignsApi from "@/services/projects/UmbrellaCampaignsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { object, mixed } from "yup";
import { ref, computed, watch } from "vue";
import { useForm } from "vee-validate";
import { useStageManagement } from "@/composables/useStageManagement";
import { UmbrellaStageCategoryLCategoryData } from "@/services/UtilsApi";

const { data, goBack, goNext, saveData } =
  useMultiStepFormContext<UmbrellaCampaignData>();
const brandId = useBrandId();
const { t } = useI18n();
const projectId = useProjectId();

// Usar el composable para gestión de stages
const {
  stageCategoryList,
  selectedCategory,
  selectedStageNames,
  allSelectedStagesFull,
  totalSelectedStagesCount,
  isLoading,
  error,
  initializeStageList,
  getCurrentCategoryStages,
  updateStageText,
  addStageToCurrentCategory,
  removeStageFromSelection,
  setSelectedCategory,
  setSelectedStages,
  setSavedStages, // Función para establecer stages guardadas
  initializeFromSavedData,
  getStoryStagesForSaving,
  validateStageSelection, // Validación global incluyendo guardadas
} = useStageManagement();

const REQUIRED_STAGE_COUNT = 3;

// Obtener stages guardadas de los datos
const stagesSelectedFromData = data.value.story_stages || [];
// Establecer stages guardadas en el composable
setSavedStages(stagesSelectedFromData);

// Inicialización  de la lista de stages
const initializeStages = async () => {
  let stageCategories: UmbrellaStageCategoryLCategoryData[] = [];
  // Prioridad: datos guardados en la campaña
  if (
    Array.isArray(data.value.categories_stages) &&
    data.value.categories_stages.length > 0
  ) {
    stageCategories = data.value.categories_stages;
  } else {
    // Si no hay datos guardados, obtener del API
    try {
      const response =
        await UmbrellaCampaignsApi.GenerateUmbrellaStageCategoryList(
          brandId,
          projectId,
          data.value.id,
        );
      stageCategories = response.data || [];
    } catch (e) {
      console.error("Error fetching stage categories:", e);
      stageCategories = [];
    }
  }
  await initializeStageList(stageCategories);
};
await initializeStages();

// Schema de validación simplificado
const schema = computed(() =>
  toTypedSchema(
    object().shape({
      selectedCategory: mixed().required(
        t(
          "umbrella-campaign.step-scene.stages.validation.selected-category-required",
        ),
      ),
    }),
  ),
);

// Valores iniciales del formulario
const initialValues = {
  selectedCategory: "",
};

// Computed para validación global (incluye stages guardadas)
const isGlobalValidationValid = computed((): boolean => {
  const validation = validateStageSelection(REQUIRED_STAGE_COUNT);
  return validation.isValid;
});

// Computed para mensaje de error global
const globalValidationMessage = computed((): string => {
  const validation = validateStageSelection(REQUIRED_STAGE_COUNT);
  return validation.message;
});

const { handleSubmit, isSubmitting, errors, submitCount, setFieldValue, meta } =
  useForm({
    validationSchema: schema,
    initialValues: initialValues,
  });

// Inicializar desde datos guardados
initializeFromSavedData(data.value);

// Sincronización entre el composable y el formulario
watch(selectedCategory, (val) => {
  setFieldValue("selectedCategory", val === null ? "" : val);
});

// Computed para manejar la selección de stages de forma reactiva
const selectedStagesByCategory = computed({
  get(): string[] {
    return selectedStageNames.value;
  },
  set(val: string[]): void {
    setSelectedStages(val);
  },
});

// Handlers para eventos de componentes hijos
function handleCategoryChange(categoryName: string): void {
  setSelectedCategory(categoryName);
}

function handleStagesChange(stageNames: string[]): void {
  setSelectedStages(stageNames);
}

function handleUpdateContext({
  name,
  value,
}: {
  name: string;
  value: string;
}): void {
  updateStageText(name, value);
}

function handleRemoveStage(name: string): void {
  removeStageFromSelection(name);
}

// Gestión de modales
const showCustomStageModal = ref<boolean>(false);
const showContextStageModal = ref<boolean>(false);
const contextStageData = ref<{
  name: string;
  display_name: string;
  avatar: string;
  context: string;
}>({
  name: "",
  display_name: "",
  avatar: "",
  context: "",
});

function handleAddCustomStage(): void {
  showCustomStageModal.value = true;
}

async function handleCustomStageAdded(newStage: {
  name: string;
  display_name: string;
  context: string;
}): Promise<void> {
  addStageToCurrentCategory(newStage);
}

function handleEditStageContext(stage: any): void {
  contextStageData.value = {
    ...stage,
    context: stage.text || stage.context || "",
  };
  showContextStageModal.value = true;
}

function handleSaveContextStage({
  name,
  context,
}: {
  name: string;
  context: string;
}): void {
  updateStageText(name, context);
  showContextStageModal.value = false;
}

//  Submit del formulario
const onSubmit = handleSubmit(async (_values) => {
  // Verificar validación global (incluye stages guardadas)
  if (!isGlobalValidationValid.value) {
    console.error(
      "Global stage validation failed:",
      globalValidationMessage.value,
    );
    return false;
  }

  // Preparar datos para el API (incluye stages guardadas + seleccionadas)
  const storyStagesData = getStoryStagesForSaving();
  const response = await UmbrellaCampaignsApi.SettingStoryStages(
    brandId,
    projectId,
    data.value.id,
    storyStagesData,
  );
  saveData(response.data);
  goNext();
});

// Computed para obtener los stages de la categoría seleccionada
const stagesOfSelectedCategory = computed(() => getCurrentCategoryStages());
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="scene" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=h3RLoihDatg"
    >
      {{ $t("umbrella-campaign.step-scene.stages.title") }}
      <template #description>
        {{ $t("umbrella-campaign.step-scene.stages.subtitle") }}
      </template>
    </PageTitle>

    <!-- Loading state -->
    <div v-if="isLoading" class="tw:flex tw:justify-center tw:py-8">
      <CircleLoader />
    </div>

    <!-- Error state -->
    <Alert v-else-if="error" type="error" class="tw:mb-6">
      {{ error }}
    </Alert>

    <!-- Main content -->
    <template v-else>
      <StageCardSelectable
        v-if="stageCategoryList.length > 0"
        :categories="stageCategoryList"
        :modelValue="selectedCategory"
        @update:modelValue="handleCategoryChange"
      />

      <FieldError
        v-if="submitCount > 0 && errors.selectedCategory && !selectedCategory"
      >
        {{ errors.selectedCategory }}
      </FieldError>

      <StageCardStageSelectable
        v-if="selectedCategory"
        :stages="stagesOfSelectedCategory"
        :modelValue="selectedStagesByCategory"
        @update:modelValue="handleStagesChange"
        class="tw:mt-10"
        @add-custom-stage="handleAddCustomStage"
        @edit-stage-context="handleEditStageContext"
      />

      <SelectedStageCards
        :stages="allSelectedStagesFull"
        :maxStages="REQUIRED_STAGE_COUNT"
        :currentCount="totalSelectedStagesCount"
        @update-context="handleUpdateContext"
        @remove-stage="handleRemoveStage"
        class="tw:mt-12"
      />
    </template>

    <!-- Modales -->
    <UmbrellaCampaingnNewStageModal
      v-model="showCustomStageModal"
      @add-stage="handleCustomStageAdded"
    />

    <UmbrellaCampaingContextStageModal
      v-if="showContextStageModal"
      v-model="showContextStageModal"
      v-bind="contextStageData"
      @save-context="handleSaveContextStage"
      @close="showContextStageModal = false"
    />

    <!--  Error de validación global (incluye stages guardadas) -->
    <Alert
      v-if="submitCount > 0 && !isGlobalValidationValid"
      type="error"
      autoScroll
    >
      {{ globalValidationMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
