<script lang="ts" setup>
import { useField } from "vee-validate";
import { RefinerCategory } from "./categoryRefinerTypes";
import { useCategoryRefiner } from "./useCategoryRefiner";
import { ModalAskLucaRefinerProps } from "./ModalAskLucaRefiner.vue";
import CategoryRefinerGrouped from "./CategoryRefinerGrouped.vue";

interface AttributeItem {
  id: string;
  idx: number;
}
export interface MandatoryAttributeGroup {
  id: string;
  idx: number;
  items: AttributeItem[];
  display_name: string;
}

export type CategoryRefinerFieldAskLuca = Record<
  string,
  Omit<ModalAskLucaRefinerProps, "name">
>;

interface CategoryRefinerFieldGroupedProps {
  name: string;
  askLuca?: CategoryRefinerFieldAskLuca;
  disabled?: boolean;
  create?: boolean;
  // No es necesario maxItems aquí, ya que es por categoría en RefinerCategory
  newCategoryDefaultProps?: Partial<RefinerCategory>;
  // Prop para recibir la estructura de agrupación
  groups: MandatoryAttributeGroup[];
}

const props = defineProps<CategoryRefinerFieldGroupedProps>();
const { t, te } = useI18n();

const { errorMessage, handleChange, meta } = useField<RefinerCategory[]>(
  () => props.name,
);

// Esto es crucial para que las tarjetas puedan modificar su propio estado.
const { data: allCategories } = useCategoryRefiner(meta.initialValue);

// Sincronizamos los cambios del estado reactivo de vuelta al campo del formulario
watch(allCategories, (newData) => {
  handleChange(newData, !!errorMessage.value);
});

// Propiedad computada para procesar y agrupar las categorías
const groupedData = computed(() => {
  if (!props.groups || !allCategories.value) {
    return [];
  }
  // Creamos un mapa para una búsqueda eficiente de categorías por su nombre/id
  const categoriesMap = new Map(
    allCategories.value.map((cat) => [cat.name, cat]),
  );

  return props.groups
    .map((group) => {
      // Para cada grupo, encontramos sus categorías correspondientes
      const groupCategories = group.items
        .map((item) => categoriesMap.get(item.id))
        .filter((cat): cat is RefinerCategory => !!cat); // Filtramos las no encontradas

      const i18nKey = `category-refiner.groups.${group.id}`;
      const displayName = te(i18nKey) ? t(i18nKey) : group.display_name;

      return {
        id: group.id,
        displayName,
        categories: groupCategories,
      };
    })
    .filter((group) => group.categories.length > 0); // Solo incluimos grupos que tengan categorías
});
</script>

<template>
  <div class="tw:space-y-10">
    <!-- Iteramos sobre los datos  agrupados -->
    <div v-for="group in groupedData" :key="group.id" class="tw:space-y-6">
      <div class="tw:flex tw:items-center tw:gap-6">
        <h2 class="tw:min-w-fit tw:text-lg tw:font-extrabold">
          {{ group.displayName }}
        </h2>
        <Separator />
      </div>

      <CategoryRefinerGrouped
        :create="props.create"
        :newCategoryDefaultProps="props.newCategoryDefaultProps"
        :askLuca="props.askLuca"
        :disabled="props.disabled"
        :categories="group.categories"
      />
    </div>
  </div>

  <Alert v-if="errorMessage" type="error">
    {{ te(errorMessage) ? t(errorMessage) : errorMessage }}
  </Alert>
</template>
