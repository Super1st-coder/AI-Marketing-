<script lang="ts" setup>
import { useField } from "vee-validate";
import { CategorySelector } from "./categorySelectorTypes";

interface CategoryRefinerFieldProps {
  name: string;
  openCard?: boolean;
}

const props = withDefaults(defineProps<CategoryRefinerFieldProps>(), {
  openCard: false,
});
const { t, te } = useI18n();

const { value: category } = useField<CategorySelector>(
  () => props.name,
  undefined,
);

const isOpen = ref(props.openCard);
const toggle = () => {
  isOpen.value = !isOpen.value;
};
</script>

<template>
  <CardBase
    class="tw:flex tw:flex-col tw:p-4"
    :class="{ 'tw:gap-5': isOpen, 'tw:gap-1.5': !isOpen }"
  >
    <h3 class="tw:text-lg tw:font-extrabold">
      {{
        te(`category-refiner.titles.${category.name}`)
          ? t(`category-refiner.titles.${category.name}`)
          : snakeCaseToText(category.name)
      }}
    </h3>

    <div v-if="isOpen" class="tw:flex tw:flex-col tw:gap-2">
      <div v-for="(_item, index) in category.items">
        <CategorySelectorCardItem :name="`${props.name}.items[${index}]`" />
      </div>
    </div>

    <button
      class="tw:flex tw:w-full tw:justify-center"
      @click="toggle"
      type="button"
    >
      <Icon
        :icon="isOpen ? 'tabler-chevron-up' : 'tabler-chevron-down'"
        class="tw:text-2xl"
      />
    </button>
  </CardBase>
</template>
