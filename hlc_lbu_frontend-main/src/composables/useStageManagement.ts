import { ref, reactive, computed, nextTick } from "vue";
import UtilsApi from "@/services/UtilsApi";
import type { UmbrellaCampaignStoryStageItem } from "@/services/projects/UmbrellaCampaignsApi";

interface Stage {
  name: string;
  display_name: string;
  text?: string;
  avatar?: string;
  context?: string;
  categoryName?: string;
}

interface Category {
  name: string;
  display_name: string;
  stages: Stage[];
}

interface StageValidationResult {
  isValid: boolean;
  count: number;
  message: string;
}

interface StoryStagesResponse {
  story_stages: UmbrellaCampaignStoryStageItem[];
}

/**
 * Composable para gestión reactiva de stages en Umbrella Campaigns Scene
 */
export function useStageManagement() {
  // Importar i18n
  const { t } = useI18n();

  // Estado reactivo
  const stageCategoryList = ref<Category[]>([]);
  const selectedCategory = ref<string | null>(null);
  const selectionsByCategory = ref<Record<string, string[]>>({});
  const stagesFromSavedData = ref<Stage[]>([]); //  Stages guardadas
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  /**
   * Computed que devuelve las stages seleccionadas de la categoría actual
   */
  const selectedStageNames = computed({
    get(): string[] {
      if (!selectedCategory.value) return [];
      return selectionsByCategory.value[selectedCategory.value] || [];
    },
    set(stageNames: string[]) {
      if (!selectedCategory.value) return;
      selectionsByCategory.value[selectedCategory.value] = [...stageNames];
    },
  });

  /**
   * Computed que devuelve los stages seleccionados completos de la categoría actual
   */
  const selectedStagesFull = computed((): Stage[] => {
    if (!selectedCategory.value || !stageCategoryList.value) return [];
    const cat = stageCategoryList.value.find(
      (c) => c.name === selectedCategory.value,
    );
    if (!cat) return [];

    return cat.stages.filter((stage) =>
      selectedStageNames.value.includes(stage.name),
    );
  });

  /**
   * Computed que devuelve TODAS las stages seleccionadas de TODAS las categorías + guardadas
   */
  const allSelectedStagesFull = computed((): Stage[] => {
    const allSelected: Stage[] = [];

    // Agregar stages seleccionadas manualmente
    Object.keys(selectionsByCategory.value).forEach((categoryName) => {
      const category = stageCategoryList.value.find(
        (c) => c.name === categoryName,
      );
      if (category) {
        const selectedStageNamesInCategory =
          selectionsByCategory.value[categoryName] || [];
        selectedStageNamesInCategory.forEach((stageName) => {
          const stage = category.stages.find((s) => s.name === stageName);
          if (stage) {
            allSelected.push({
              ...stage,
              categoryName: categoryName, // Agregar info de categoría
            });
          }
        });
      }
    });

    //  Agregar stages guardadas previamente
    stagesFromSavedData.value.forEach((savedStage) => {
      const alreadySelected = allSelected.some(
        (stage) => stage.name === savedStage.name,
      );
      if (!alreadySelected) {
        allSelected.push(savedStage);
      }
    });

    return allSelected;
  });

  /**
   *  Computed que devuelve el total de stages seleccionadas
   */
  const totalSelectedStagesCount = computed((): number => {
    return allSelectedStagesFull.value.length;
  });

  /**
   * Computed que devuelve la categoría actual
   */
  const currentCategory = computed((): Category | null => {
    if (!selectedCategory.value || !stageCategoryList.value) return null;
    return (
      stageCategoryList.value.find((c) => c.name === selectedCategory.value) ||
      null
    );
  });

  /**
   *  Establece las stages guardadas desde datos del servidor
   */
  const setSavedStages = (savedStages: any[]): void => {
    // Convertir stages guardadas al formato interno
    stagesFromSavedData.value = savedStages.map((savedStage) => ({
      name: savedStage.name,
      display_name: savedStage.display_name,
      text: savedStage.text || "",
      categoryName: savedStage.stage?.name || "saved", // Usar la categoría real del servidor
    }));
  };

  /**
   * Inicializa la lista de categorías de stages
   */
  const initializeStageList = async (initialData?: Category[]) => {
    try {
      isLoading.value = true;
      error.value = null;

      if (initialData) {
        // Convertir a reactivo si se proporciona data inicial
        stageCategoryList.value = reactive(
          JSON.parse(JSON.stringify(initialData)),
        );
      } else {
        // Cargar desde API
        //TODO: cambiar servicio por Generate Categories and Stages By Umbrella Campaign
        /* const { data } = await UtilsApi.getUmbrellaStageCategoryList();
        if (data) {
          stageCategoryList.value = reactive(JSON.parse(JSON.stringify(data)));
        }*/
      }

      // Inicializar selecciones vacías para cada categoría si no existen
      stageCategoryList.value.forEach((category) => {
        if (!selectionsByCategory.value[category.name]) {
          selectionsByCategory.value[category.name] = [];
        }
      });
    } catch (err) {
      error.value = "Error loading stage categories";
      console.error("Error initializing stage list:", err);
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Refrescar la lista desde el servidor
   */
  const refreshStageList = async () => {
    try {
      isLoading.value = true;
      const { data } = await UtilsApi.getUmbrellaStageCategoryList();
      if (data) {
        const currentSelections = { ...selectionsByCategory.value };

        // Actualizar la lista de categorías
        Object.assign(stageCategoryList.value, data);

        // Restaurar selecciones, filtrando solo las que siguen existiendo
        nextTick(() => {
          Object.keys(currentSelections).forEach((categoryName) => {
            const category = stageCategoryList.value.find(
              (c) => c.name === categoryName,
            );
            if (category) {
              // Filtrar solo stages que aún existen en la categoría
              const validSelections = currentSelections[categoryName].filter(
                (stageName) =>
                  category.stages.some((stage) => stage.name === stageName),
              );
              selectionsByCategory.value[categoryName] = validSelections;
            }
          });
        });
      }
    } catch (err) {
      error.value = "Error refreshing stage list";
      console.error("Error refreshing stage list:", err);
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Obtiene los stages de la categoría seleccionada
   */
  const getCurrentCategoryStages = (): Stage[] => {
    if (!selectedCategory.value || !stageCategoryList.value) return [];
    const category = stageCategoryList.value.find(
      (c) => c.name === selectedCategory.value,
    );
    return category ? category.stages : [];
  };

  /**
   * Actualiza el texto de un stage específico (tanto guardadas como manuales)
   */
  const updateStageText = (stageName: string, newText: string): boolean => {
    // Buscar primero en stages guardadas
    const savedStage = stagesFromSavedData.value.find(
      (s) => s.name === stageName,
    );
    if (savedStage) {
      savedStage.text = newText;
      return true;
    }

    // Buscar en todas las categorías
    for (const category of stageCategoryList.value) {
      const stage = category.stages.find((s) => s.name === stageName);
      if (stage) {
        stage.text = newText;
        return true;
      }
    }
    return false;
  };

  /**
   * Agrega un nuevo stage a la categoría seleccionada y lo selecciona automáticamente
   */
  const addStageToCurrentCategory = (newStage: {
    name: string;
    display_name: string;
    context: string;
    avatar?: string;
  }): boolean => {
    const category = currentCategory.value;
    if (!category) return false;

    // Verificar si ya existe
    if (category.stages.some((s) => s.name === newStage.name)) {
      console.warn(`Stage with name "${newStage.name}" already exists`);
      return false;
    }

    // Agregar el nuevo stage
    const stageToAdd: Stage = {
      name: newStage.name,
      display_name: newStage.display_name,
      text: newStage.context || "",
      avatar: newStage.avatar,
    };

    category.stages.push(stageToAdd);

    // Agregar a la selección SIN perder las existentes
    const currentSelections = selectedStageNames.value;
    selectedStageNames.value = [...currentSelections, newStage.name];

    return true;
  };

  /**
   * Selecciona/deselecciona un stage
   */
  const toggleStageSelection = (stageName: string): void => {
    const current = selectedStageNames.value;
    if (current.includes(stageName)) {
      selectedStageNames.value = current.filter((s) => s !== stageName);
    } else {
      selectedStageNames.value = [...current, stageName];
    }
  };

  /**
   *  Remueve un stage de la selección
   */
  const removeStageFromSelection = (stageName: string): void => {
    // Buscar en stages guardadas y remover
    const savedIndex = stagesFromSavedData.value.findIndex(
      (stage) => stage.name === stageName,
    );
    if (savedIndex > -1) {
      stagesFromSavedData.value.splice(savedIndex, 1);
      return;
    }

    // Buscar en qué categoría está el stage y removerlo
    Object.keys(selectionsByCategory.value).forEach((categoryName) => {
      const stageIndex =
        selectionsByCategory.value[categoryName].indexOf(stageName);
      if (stageIndex > -1) {
        selectionsByCategory.value[categoryName].splice(stageIndex, 1);
      }
    });
  };

  /**
   * Establece la categoría seleccionada SIN limpiar selecciones
   */
  const setSelectedCategory = (categoryName: string | null): void => {
    selectedCategory.value = categoryName;
    // NO limpiar selecciones - mantener las selecciones de cada categoría
    if (categoryName && !selectionsByCategory.value[categoryName]) {
      selectionsByCategory.value[categoryName] = [];
    }
  };

  /**
   * Establece los stages seleccionados para la categoría actual
   */
  const setSelectedStages = (stageNames: string[]): void => {
    selectedStageNames.value = stageNames; // Usa el computed setter
  };

  /**
   * Inicializa las selecciones desde datos guardados
   */
  const initializeFromSavedData = (savedData: any): void => {
    if (!savedData || !stageCategoryList.value) return;

    // Si hay stages seleccionados guardados
    if (savedData.stages_selected && Array.isArray(savedData.stages_selected)) {
      const stagesByCategory = savedData.stages_selected.reduce(
        (acc: any, stage: any) => {
          const categoryName = stage.stage?.name;
          if (categoryName) {
            if (!acc[categoryName]) acc[categoryName] = [];
            acc[categoryName].push(stage.name);
          }
          return acc;
        },
        {},
      );

      // Establecer selecciones por categoría
      Object.keys(stagesByCategory).forEach((categoryName) => {
        selectionsByCategory.value[categoryName] =
          stagesByCategory[categoryName];
      });

      // Establecer la primera categoría que tenga selecciones como activa
      const firstCategoryWithSelections = Object.keys(stagesByCategory)[0];
      if (firstCategoryWithSelections) {
        setSelectedCategory(firstCategoryWithSelections);
      }
    }
  };

  /**
   *  Función que retorna el objeto story_stages con el formato requerido para el API (incluye guardadas)
   */
  const getStoryStagesForSaving = (): StoryStagesResponse => {
    // Asignar id según la posición en el array (0,1,2,...) respetando el orden actual
    const storyStages: UmbrellaCampaignStoryStageItem[] =
      allSelectedStagesFull.value.map((stage, index) => ({
        id: index,
        name: stage.name,
        display_name: stage.display_name,
        text: stage.text || stage.context || "",
        stage: {
          name: stage.name,
          display_name: stage.display_name,
        },
      }));

    return {
      story_stages: storyStages,
    };
  };

  /**
   *  Valida si se cumple con el mínimo y máximo de stages requeridas (incluye guardadas)
   */
  const validateStageSelection = (
    stageCount: number = 3,
  ): StageValidationResult => {
    const count = totalSelectedStagesCount.value;
    let message = "";

    if (count !== stageCount) {
      message = t(
        "umbrella-campaign.step-scene.stages.validation.stages-to-continue",
        {
          min: stageCount,
        },
      );
    } else {
      message = t(
        "umbrella-campaign.step-scene.stages.validation.valid-selection",
      );
    }

    return {
      isValid: count === stageCount,
      count,
      message,
    };
  };

  /**
   * Obtiene el estado actual para guardado
   */
  const getStateForSaving = () => {
    return {
      selectedCategory: selectedCategory.value,
      selectedStages: selectedStageNames.value, // Solo de la categoría actual
      selectionsByCategory: selectionsByCategory.value, // Todas las selecciones
      stageCategoryList: stageCategoryList.value,
      selectedStagesFull: selectedStagesFull.value,
      allSelectedStagesFull: allSelectedStagesFull.value, //  Todas las stages de todas las categorías + guardadas
      totalSelectedStagesCount: totalSelectedStagesCount.value, //  Total incluyendo guardadas (corregido)
      storyStages: getStoryStagesForSaving(), //Formato para API usando UmbrellaCampaignStoryStageItem
    };
  };

  return {
    // Estado reactivo
    stageCategoryList,
    selectedCategory,
    selectedStageNames, // Computed que maneja categoría actual
    selectionsByCategory, // Selecciones por categoría
    stagesFromSavedData, //  Stages guardadas
    isLoading,
    error,

    // Computed properties
    selectedStagesFull, // Stages de categoría actual
    allSelectedStagesFull, // Todas las stages de todas las categorías + guardadas
    totalSelectedStagesCount, //  Total de stages seleccionadas (corregido para mejor reactividad)
    currentCategory,

    // Métodos
    initializeStageList,
    refreshStageList,
    getCurrentCategoryStages,
    updateStageText, //  Actualizada para manejar guardadas
    addStageToCurrentCategory,
    toggleStageSelection,
    removeStageFromSelection, // Actualizada con logs de debug
    setSelectedCategory,
    setSelectedStages,
    setSavedStages, // Función para establecer stages guardadas
    initializeFromSavedData,
    getStateForSaving,
    getStoryStagesForSaving, //Formato story_stages incluyendo guardadas
    validateStageSelection, //  Validación global incluyendo guardadas
  };
}
