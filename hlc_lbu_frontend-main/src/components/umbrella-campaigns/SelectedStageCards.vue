<script setup lang="ts">
interface Stage {
  name: string;
  display_name: string;
  avatar?: string;
  context?: string;
  text?: string;
  categoryName?: string;
}

const props = defineProps<{
  stages: Stage[];
  maxStages: number;
  currentCount?: number;
}>();

const emit = defineEmits(["update-context", "remove-stage"]);

// Computed para asegurar reactividad en el texto de cada stage
const reactiveStages = computed(() =>
  props.stages.map((stage) => ({
    ...stage,
    text: stage.text || stage.context || "",
  })),
);

//  Computed para mostrar el contador correctamente (incluye stages guardadas)
const stageCount = computed(() => {
  return props.currentCount !== undefined
    ? props.currentCount
    : props.stages.length;
});

const remainingStages = computed(() => {
  const remaining = props.maxStages - stageCount.value;
  return Math.max(0, remaining);
});

function handleEdit(stage: Stage, value: string) {
  emit("update-context", { name: stage.name, value });
}

function handleRemove(stage: Stage) {
  emit("remove-stage", stage.name);
}

//  Función para mostrar el texto de categoría apropiado
/*function getCategoryDisplayText(categoryName: string): string {
  // Buscar la categoría en las disponibles para obtener el display_name
  // Si no se encuentra, mostrar el nombre de la categoría o "From saved data"
  if (categoryName === 'saved') {
    return 'From saved data';
  }
  
  // Capitalizar primera letra y reemplazar guiones/underscores con espacios
  return categoryName
    .split(/[-_]/) 
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}*/
</script>

<template>
  <div>
    <!-- ✅ Header que muestra el contador total incluyendo stages guardadas -->
    <h3 class="tw:mb-2 tw:text-xl tw:font-bold">
      {{
        $t("umbrella-campaign.step-scene.stages.selected-header", {
          count: stageCount,
          max: maxStages,
        })
      }}
    </h3>
    <p class="tw:mb-6 tw:text-sm tw:text-gray-500">
      <span v-if="remainingStages > 0">
        {{
          $t("umbrella-campaign.step-scene.stages.select-more", {
            remaining: remainingStages,
            plural: remainingStages !== 1 ? "s" : "",
          })
        }}
      </span>
      <span v-else-if="stageCount === maxStages" class="tw:text-green-600">
        {{
          $t("umbrella-campaign.step-scene.stages.perfect", { max: maxStages })
        }}
      </span>
      <span v-else class="tw:text-red-600">
        {{
          $t("umbrella-campaign.step-scene.stages.too-many", {
            extra: stageCount - maxStages,
            plural: stageCount - maxStages !== 1 ? "s" : "",
          })
        }}
      </span>
    </p>

    <!-- Grid que muestra TODAS las stages: guardadas + seleccionadas manualmente -->
    <div class="tw:grid tw:grid-cols-1 tw:gap-6 tw:lg:grid-cols-3">
      <div
        v-for="stage in reactiveStages"
        :key="stage.name"
        class="tw:relative tw:flex tw:flex-col tw:gap-2 tw:rounded-xl tw:bg-white tw:p-4 tw:shadow"
      >
        <div class="tw:mb-2 tw:flex tw:items-center tw:gap-2">
          <div class="tw:flex tw:flex-col">
            <span class="tw:text-base tw:font-semibold">{{
              stage.display_name
            }}</span>
          </div>
          <!--  Botón de remover funciona para ambos tipos -->
          <button
            @click="handleRemove(stage)"
            type="button"
            class="tw:ml-auto tw:flex tw:cursor-pointer tw:items-center tw:justify-center tw:rounded-full tw:bg-gray-100 tw:p-1 tw:transition-colors tw:hover:bg-gray-200"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="10" fill="#E5E7EB" />
              <path
                d="M13 7L7 13M7 7l6 6"
                stroke="#6B7280"
                stroke-width="2"
                stroke-linecap="round"
              />
            </svg>
          </button>
        </div>

        <div
          class="tw:flex tw:items-center tw:gap-2 tw:rounded-lg tw:bg-gray-100 tw:p-3"
        >
          <FieldEditableText
            :name="`selected.${stage.name}.text`"
            :modelValue="stage.text"
            @update:modelValue="(value) => handleEdit(stage, value)"
            :placeholder="
              $t('umbrella-campaign.step-scene.stages.context-placeholder')
            "
            required
            type="textarea"
            variant="default"
            color="normal"
            class="tw:flex-1"
          />
        </div>
      </div>
    </div>
  </div>
</template>
