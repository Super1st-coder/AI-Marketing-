<script lang="ts" setup>
import { BuyerPersonData } from "@/services/BuyerPersonasApi";
import { RouterLink } from "vue-router";

interface Props {
  data: BuyerPersonData;
  interactable?: boolean;
}

defineProps<Props>();
</script>

<template>
  <CardBase class="tw:p-3">
    <!-- Image -->
    <component
      :is="interactable ? RouterLink : 'div'"
      :to="
        interactable
          ? {
              name: 'BuyerPersonSettings',
              params: { buyerPersonId: data.id },
            }
          : undefined
      "
    >
      <CardDynamicImage
        class="tw:mb-4 tw:aspect-square"
        :src="data.thumbnail_url ?? undefined"
      />
    </component>

    <!-- Title -->
    <component
      :is="interactable ? RouterLink : 'div'"
      :to="
        interactable
          ? {
              name: 'BuyerPersonSettings',
              params: { buyerPersonId: data.id },
            }
          : undefined
      "
    >
      <h2 class="tw:mb-2.5 tw:text-sm tw:font-bold">
        {{ data.name ?? data.description_01 }}
      </h2>
    </component>

    <!-- Chips -->
    <ChipList>
      <ChipCompleted :completed="data.complete" />
      <ChipLocked :locked="data.locked" />
    </ChipList>
  </CardBase>
</template>
