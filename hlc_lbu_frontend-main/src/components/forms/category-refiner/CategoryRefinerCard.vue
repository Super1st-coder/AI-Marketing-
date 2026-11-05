<script lang="ts" setup>
import { ModalAskLucaRefinerProps } from "@/components/forms/category-refiner/ModalAskLucaRefiner.vue";
import { RefinerCategory, RefinerItem } from "./categoryRefinerTypes";
import { useCategoryRefinerData } from "./useCategoryRefiner";

interface Props {
  category: RefinerCategory;
  askLuca?: Omit<ModalAskLucaRefinerProps, "name">;
  errorMessage?: string;
}

const props = defineProps<Props>();
const { data } = useCategoryRefinerData();
const { t, te } = useI18n();

const error = ref<[string, number] | undefined>();
const selectedCount = computed(
  () => props.category.items.filter((item) => item.checked).length,
);

const maxItemsReached = computed(() => {
  return (
    props.category.maxItems !== undefined &&
    selectedCount.value > props.category.maxItems
  );
});
// The card can be saved if the minimum amount of items is selected and the maximum amount is not exceeded.
const canBeSaved = computed(() => {
  if (!props.category.minimumItems) {
    return true;
  }

  return selectedCount.value >= props.category.minimumItems;
});

const setCategory = (categoryData: Partial<RefinerCategory>) => {
  data.value = data.value.map((category) => {
    // If the category is this one
    if (category.name === props.category.name) {
      // Add the data
      return {
        ...category,
        ...categoryData,
      };
    }

    return category;
  });
};

const handleDelete = () => {
  data.value = data.value.filter(
    (category) => category.name !== props.category.name,
  );
};

const addItemName = ref<string>("");

const handleAddItem = () => {
  // If the input has a value
  if (addItemName.value) {
    const isDuplicated = props.category.items.find(
      (item) => item.name === addItemName.value,
    );

    if (!isDuplicated) {
      setCategory({
        items: [...props.category.items, { name: addItemName.value }],
      });

      addItemName.value = "";
    }
  }
};

const handleSave = () => {
  if (canBeSaved.value && !maxItemsReached.value) {
    setCategory({ isSaved: true, isOpen: false });
    error.value = undefined;
    wasSaved.value = true;
  } else {
    if (!canBeSaved.value) {
      // No se han seleccionado suficientes ítems
      error.value = [
        "category-refiner.errors.you-need-to-select-at-least-n-items",
        props.category.minimumItems ?? 0, // Usar 0 como fallback
      ];
    } else if (maxItemsReached.value) {
      // Se han seleccionado demasiados ítems
      error.value = [
        "category-refiner.errors.you-cant-select-more-than-n-items",
        props.category.maxItems ?? 0,
      ];
    }
    setCategory({ isSaved: false }); // Asegurarse de que no se guarde si la validación falla
  }
};

const wasSaved = ref<boolean | undefined>(props.category.isSaved);

const close = () => {
  if (wasSaved.value) {
    handleSave();
    setCategory({ isOpen: false });
  } else {
    setCategory({ isOpen: false, hasBeenClosed: true });
  }
};

const open = () => {
  setCategory({
    isOpen: true,
    hasBeenOpened: true,
  });
};

const toggle = () => {
  if (props.category.isOpen) {
    close();
  } else {
    open();
  }
};

// Remove the error if the minimum amount of items has been selected
watch(selectedCount, (selectedCount) => {
  if (
    props.category.minimumItems &&
    error.value &&
    selectedCount >= props.category.minimumItems
  ) {
    error.value = undefined;
  }
});

// Add error if the minimum amount of items is not reached
watch(canBeSaved, (canBeSaved) => {
  if (wasSaved.value && !canBeSaved) {
    // Si estaba guardado, pero ahora el mínimo no se cumple
    error.value = [
      "category-refiner.errors.you-need-to-select-at-least-n-items",
      props.category.minimumItems ?? 0,
    ];
    setCategory({ isSaved: false });
  } else if (wasSaved.value && canBeSaved && !maxItemsReached.value) {
    // Si estaba guardado, y ahora el mínimo se cumple y el máximo no se excede, limpiar error
    error.value = undefined;
    setCategory({ isSaved: true });
  }
});

// Nuevo watch para maxItemsReached para manejar errores y desguardar
watch(maxItemsReached, (isMaxReached) => {
  if (wasSaved.value && isMaxReached) {
    // Si estaba guardado, pero ahora el máximo se excede
    error.value = [
      "category-refiner.errors.you-cant-select-more-than-n-items",
      props.category.maxItems ?? 0,
    ];
    setCategory({ isSaved: false });
  } else if (wasSaved.value && !isMaxReached && canBeSaved.value) {
    // Si estaba guardado, y ahora el máximo no se excede y el mínimo se cumple, limpiar error
    error.value = undefined;
    setCategory({ isSaved: true });
  }
});

// Complete category if it was saved before and the minimum amount of items has been selected
watch(canBeSaved, (canBeSaved) => {
  if (wasSaved.value && canBeSaved) {
    setCategory({ isSaved: true });
  }
});

const highlightType = computed(() => {
  if (
    error.value ||
    (props.category.minimumItems && props.category.items.length === 0) ||
    (props.category.minimumItems &&
      props.category.hasBeenClosed &&
      selectedCount.value < props.category.minimumItems) ||
    (props.category.minimumItems &&
      props.category.hasBeenClosed &&
      !props.category.isOpen &&
      !props.category.isSaved) ||
    // If there's a general error and the category is not saved
    (props.errorMessage && !props.category.isSaved)
  ) {
    return "error";
  }

  if (
    !error.value &&
    !props.category.isSaved &&
    !props.category.minimumItems &&
    props.category.items.length === 0
  ) {
    return "warning";
  }

  if (props.category.isSaved) {
    return "success";
  }

  return null;
});

// Open up the card if a general error is shown
watch(
  () => props.errorMessage,
  (errorMessage) => {
    if (errorMessage && !props.category.isSaved) {
      open();

      if (!canBeSaved.value && props.category.minimumItems) {
        error.value = [
          "category-refiner.errors.you-need-to-select-at-least-n-items",
          props.category.minimumItems,
        ];
      }
    }
  },
);

const isAskLucaOpen = ref(false);

const handleSaveAskLucaAttributes = (attributes: string[]) => {
  setCategory({
    items: [
      ...props.category.items,
      ...attributes.map<RefinerItem>((attribute) => ({
        name: attribute,
        checked: true,
      })),
    ],
  });
};
</script>

<template>
  <CardBase
    class="tw:flex tw:flex-col tw:px-[15px] tw:py-5"
    :class="{
      'tw:gap-1.5': !category.isOpen,
      'tw:gap-5': category.isOpen,
      'tw:border-error!': highlightType === 'error',
      'tw:border-warning!': highlightType === 'warning',
    }"
    :outlineColor="
      highlightType === 'error'
        ? 'error'
        : highlightType === 'warning'
          ? 'warning'
          : undefined
    "
  >
    <div class="tw:relative tw:flex tw:flex-col tw:gap-1.5">
      <div
        class="tw:absolute tw:top-0 tw:right-0 tw:flex tw:items-center tw:gap-2"
      >
        <Icon
          v-if="highlightType"
          :icon="
            highlightType === 'success'
              ? 'tabler-check'
              : 'tabler:alert-triangle'
          "
          class="tw:text-2xl"
          :class="{
            'tw:text-success': highlightType === 'success',
            'tw:text-error': highlightType === 'error',
            'tw:text-warning': highlightType === 'warning',
          }"
        />

        <button
          v-if="category.canBeDeleted"
          type="button"
          @click="handleDelete"
          class="tw:text-[20px] tw:text-secondary"
        >
          <Icon icon="tabler-circle-x-filled" />
        </button>
      </div>

      <Chip
        v-if="!category.hasBeenOpened"
        :color="
          category.items.length > 0
            ? 'success'
            : category.minimumItems
              ? 'error'
              : 'warning'
        "
        variant="label"
        class="tw:self-start"
      >
        <template v-if="category.items.length > 0">
          {{ $t("category-refiner.new-suggestions") }}
        </template>
        <template v-else>
          {{ $t("category-refiner.no-suggestions") }}
        </template>
      </Chip>

      <h2
        class="tw:grow tw:text-lg tw:font-extrabold"
        :class="{
          'tw:pr-8': highlightType && !category.canBeDeleted,
          'tw:pr-7': !highlightType && category.canBeDeleted,
          'tw:pr-[60px]': highlightType && category.canBeDeleted,
        }"
      >
        {{
          te(`category-refiner.titles.${category.name}`)
            ? t(`category-refiner.titles.${category.name}`)
            : snakeCaseToText(category.name)
        }}
      </h2>

      <span
        v-if="category.minimumItems"
        class="tw:text-sm tw:font-normal tw:text-secondary"
      >
        {{ t("category-refiner.at-least-n", { n: category.minimumItems }) }}
      </span>

      <Chip
        v-if="category.isSaved"
        color="success"
        variant="label"
        class="tw:self-start"
      >
        {{ t("global.completed") }}
      </Chip>
    </div>

    <template v-if="category.isOpen">
      <div class="tw:flex tw:flex-col tw:gap-2.5">
        <CategoryRefinerCardItem
          v-for="item in category.items"
          :key="item.name"
          :category="category"
          :item="item"
        />

        <form @submit.prevent="handleAddItem">
          <FieldBaseText
            v-model.trim="addItemName"
            :placeholder="$t('category-refiner.add-a-new-item-placeholder')"
          />
        </form>
      </div>

      <Alert v-if="error" type="error">
        {{ $t(error[0], { n: error[1] }) }}
      </Alert>

      <div class="tw:flex tw:flex-col tw:gap-3">
        <ButtonAskLuca v-if="askLuca" @click="isAskLucaOpen = true" />

        <Button size="sm" type="button" @click="handleSave">
          {{ $t("global.save") }}
        </Button>
      </div>
    </template>

    <button
      class="tw:flex tw:w-full tw:justify-center"
      @click="toggle"
      type="button"
    >
      <Icon
        :icon="category.isOpen ? 'tabler-chevron-up' : 'tabler-chevron-down'"
        class="tw:text-2xl"
      />
    </button>

    <ModalAskLucaRefiner
      v-if="askLuca"
      v-model="isAskLucaOpen"
      :name="category.name"
      @save="handleSaveAskLucaAttributes"
      v-bind="askLuca"
    />
  </CardBase>
</template>
