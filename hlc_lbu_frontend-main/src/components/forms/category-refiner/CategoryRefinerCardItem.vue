<script lang="ts" setup>
import { RefinerCategory, RefinerItem } from "./categoryRefinerTypes";
import { useCategoryRefinerData } from "./useCategoryRefiner";

interface Props {
  category: RefinerCategory;
  item: RefinerItem;
}

const props = defineProps<Props>();

const { data } = useCategoryRefinerData();

const text = ref<string>(props.item.name);
const checked = ref(props.item.checked);

const handleDelete = () => {
  data.value = data.value.map((category) => {
    if (category.name === props.category.name) {
      return {
        ...category,
        items: category.items.filter((item) => item.name != props.item.name),
      };
    }

    return category;
  });
};

watch(text, (value) => {
  if (value.trim() === "") {
    handleDelete();
    return;
  }

  // Update the name of the item
  data.value = data.value.map((category) => {
    // If the category is the one where our item is
    if (category.name === props.category.name) {
      return {
        ...category,
        items: category.items.map((item) => {
          // If the item is the one we're editing
          if (item.name === props.item.name) {
            return {
              ...item,
              name: value,
            };
          }

          return item;
        }),
      };
    }

    return category;
  });
});

watch(checked, (value) => {
  // Check item
  data.value = data.value.map((category) => {
    // If the category is the one where our item is
    if (category.name === props.category.name) {
      return {
        ...category,
        items: category.items.map((item) => {
          // If the item is the one we're editing
          if (item.name === props.item.name) {
            return {
              ...item,
              checked: value,
            };
          }

          return item;
        }),
      };
    }

    return category;
  });
});
</script>

<template>
  <FieldBaseEditableText
    v-model.trim="text"
    v-model:checked="checked"
    checkable
    deletable
    @delete="handleDelete"
    :placeholder="$t('category-refiner.write-a-name-placeholder')"
    required
    type="textarea"
  />
</template>
