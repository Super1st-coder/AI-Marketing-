<script lang="ts" setup>
import { BuyerPersonData } from "@/services/BuyerPersonasApi";
import { getSummaryRefinerCategories } from "../forms/category-refiner/categoryRefinerTypes";
import { targetCustomerRefinerStyles } from "@/constants/target-customers";

const props = defineProps<{
  projectId: number;
  projectStep: number;
  brandId: number;
  buyerPerson: BuyerPersonData;
}>();

const emit = defineEmits<{ select: [product: BuyerPersonData] }>();

const isModalOpen = ref(false);

const mandatoryCategories = getSummaryRefinerCategories(
  props.buyerPerson.mandatory_attributes_saved,
  props.buyerPerson.mandatory_attributes_generated,
);
</script>

<template>
  <TargetCustomerCard
    :data="buyerPerson"
    is="button"
    type="button"
    class="tw:text-left"
    @click="isModalOpen = true"
  />

  <ProjectFormSelectionModal
    v-model="isModalOpen"
    :completed="buyerPerson.complete"
    :name="buyerPerson.name"
    :description="buyerPerson.bperson_story"
    :categories="mandatoryCategories"
    :categoriesStyles="targetCustomerRefinerStyles"
    :images="buyerPerson.thumbnail_url ? [buyerPerson.thumbnail_url] : []"
    :editRoute="{
      name: 'BuyerPersonSettings',
      params: { buyerPersonId: buyerPerson.id },
      query: { projectId, projectStep },
    }"
    @select="emit('select', buyerPerson)"
  />
</template>
