<script lang="ts" setup>
import { useField } from "vee-validate";
import { RefinerCategory } from "./categoryRefinerTypes";
import { useCategoryRefiner } from "./useCategoryRefiner";
import { CategoryRefinerProps } from "./CategoryRefiner.vue";
import { ModalAskLucaRefinerProps } from "@/components/forms/category-refiner/ModalAskLucaRefiner.vue";

export type CategoryRefinerFieldAskLuca = Record<
  string,
  Omit<ModalAskLucaRefinerProps, "name">
>;

interface CategoryRefinerFieldProps extends CategoryRefinerProps {
  name: string;
  askLuca?: CategoryRefinerFieldAskLuca;
  disabled?: boolean;
}

const props = defineProps<CategoryRefinerFieldProps>();
const { t, te } = useI18n();

// Use the vee-validate field
const { errorMessage, handleChange, meta } = useField<RefinerCategory[]>(
  () => props.name,
  undefined,
);

// Provide the data used by the CategoryRefiner component
const { data } = useCategoryRefiner(meta.initialValue);

// Sync the value of the field with the real data
watch(data, (newData) => {
  handleChange(newData, !!errorMessage.value);
});
</script>

<template>
  <div v-if="$slots.title" class="tw:flex tw:items-center tw:gap-6">
    <h2 v-if="$slots.title" class="tw:min-w-fit tw:text-lg tw:font-extrabold">
      <slot name="title" />
    </h2>
    <Separator />
  </div>

  <CategoryRefiner
    :create="create"
    :newCategoryDefaultProps="newCategoryDefaultProps"
    :askLuca="askLuca"
    :disabled="disabled"
    :errorMessage="errorMessage"
  />

  <Alert v-if="errorMessage" type="error" autoScroll>
    {{ te(errorMessage) ? t(errorMessage) : errorMessage }}
  </Alert>
</template>
