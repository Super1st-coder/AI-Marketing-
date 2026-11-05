<script setup lang="ts">
import { RouteLocationRaw } from "vue-router";
import {
  CategoryRefinerStyles,
  RefinerCategory,
} from "../forms/category-refiner/categoryRefinerTypes";

interface Props {
  completed?: boolean;
  name: string;
  description?: string | null;
  categories?: RefinerCategory[];
  categoriesStyles?: CategoryRefinerStyles;
  editRoute: RouteLocationRaw;
  withActions?: boolean;
  images?: string[] | null;
}

withDefaults(defineProps<Props>(), {
  completed: false,
  description: null,
  categories: () => [],
  categoriesStyles: undefined,
  withActions: true,
  images: undefined,
});

const emit = defineEmits<{ select: [] }>();

const isOpen = defineModel<boolean>({ required: true });
const isLoading = ref(false);

const handleSelect = async () => {
  isLoading.value = true;
  emit("select");
};
</script>

<template>
  <Modal
    v-model="isOpen"
    innerClass="tw:max-w-[980px] tw:py-6 tw:px-10"
    closeButton
    alignment="top"
  >
    <div class="tw:flex tw:flex-col tw:gap-10">
      <div
        class="tw:flex tw:flex-col tw:gap-5 tw:lg:flex-row tw:lg:items-start"
      >
        <div
          v-if="images?.length"
          class="tw:top-2 tw:mt-10 tw:shrink-0 tw:grow tw:lg:sticky tw:lg:order-last tw:lg:max-w-[280px]"
        >
          <ImageSlider :images="images" />
        </div>

        <div class="tw:flex tw:grow tw:flex-col tw:gap-10">
          <PageTitle is="h2">
            {{ name }}

            <ChipCompleted :completed="completed" />

            <template #description>
              <template v-if="description">{{ description }}</template>
              <template v-else>
                {{ $t("global.description-not-available") }}
              </template>
            </template>
          </PageTitle>

          <CategoryRefinerSummaryAccordions
            v-if="categories"
            :categories="categories"
            :styles="categoriesStyles"
          />
        </div>
      </div>

      <div v-if="withActions" class="tw:flex tw:justify-between">
        <ButtonGoBack class="tw:basis-[260px]" @click="isOpen = false">
          {{ $t("global.cancel") }}
        </ButtonGoBack>

        <Button
          :variant="completed ? 'label' : 'solid'"
          class="tw:basis-[260px]"
          type="button"
          :to="editRoute"
        >
          <template v-if="completed"> {{ $t("global.edit") }} </template>
          <template v-else> {{ $t("global.complete") }} </template>
        </Button>

        <Button
          class="tw:basis-[260px]"
          type="button"
          @click="handleSelect"
          :isLoading="isLoading"
          :disabled="completed === false"
        >
          {{ $t("global.select") }}
        </Button>
      </div>
    </div>
  </Modal>
</template>
