<script setup lang="ts">
import { RouteLocationRaw } from "vue-router";
import { RefinerCategory } from "../forms/category-refiner/categoryRefinerTypes";
import { CategoryRefinerStyles } from "@/components/forms/category-refiner/categoryRefinerTypes";

interface Props {
  completed?: boolean;
  name: string;
  description?: string | null;
  categories?: RefinerCategory[];
  categoriesStyles?: CategoryRefinerStyles;
  editRoute: RouteLocationRaw;
}

defineProps<Props>();
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
    innerClass="tw:max-w-[1036px] tw:py-6 tw:px-10"
    closeButton
    alignment="top"
  >
    <div class="tw:flex tw:flex-col tw:gap-10">
      <PageTitle is="h2">
        {{ name }}

        <ChipCompleted :completed="completed" />

        <template #description>
          <template v-if="description">{{ description }}</template>
          <template v-else>
            {{
              $t("campaigns.select-umbrella-campaign.modal.titlenotavailable")
            }}
          </template>
        </template>
      </PageTitle>

      <slot />

      <CategoryRefinerSummaryAccordions
        v-if="categories"
        :categories="categories"
        :styles="categoriesStyles"
      />

      <div class="tw:flex tw:justify-between">
        <ButtonGoBack class="tw:basis-[260px]" @click="isOpen = false">
          {{ $t("global.cancel") }}
        </ButtonGoBack>

        <Button
          :variant="completed ? 'label' : 'solid'"
          class="tw:basis-[260px]"
          type="button"
          :to="editRoute"
        >
          <template v-if="completed">
            {{ $t("global.edit") }}
          </template>
          <template v-else>
            {{ $t("global.complete") }}
          </template>
        </Button>

        <Button
          class="tw:basis-[260px]"
          type="button"
          @click="handleSelect"
          :isLoading="isLoading"
          :disabled="completed === false"
          >{{ $t("global.select") }}
        </Button>
      </div>
    </div>
  </Modal>
</template>
