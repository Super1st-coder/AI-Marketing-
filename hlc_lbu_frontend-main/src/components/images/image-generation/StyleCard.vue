<script lang="ts" setup>
import { CampaingStyleData } from "@/services/projects/CampaignsApi";

const props = defineProps<{
  selectedCard: CampaingStyleData | undefined;
  style: CampaingStyleData;
}>();

const emit = defineEmits<{
  (e: "select", campaign: CampaingStyleData): void; // Define un evento 'select' que pasará el objeto campaign
}>();

const handleClick = () => {
  emit("select", props.style);
};
</script>

<template>
  <CardBase
    is="button"
    @click="handleClick"
    type="button"
    :color="selectedCard?.id === props.style.id ? 'primary' : 'default'"
    :hoverColor="selectedCard === undefined ? 'primary' : undefined"
    :disabled="selectedCard !== undefined"
    class="tw:relative tw:flex tw:flex-col tw:gap-4 tw:p-4"
    :class="{
      'tw:opacity-50':
        selectedCard !== undefined && selectedCard?.id !== props.style.id,
    }"
  >
    <h2 class="tw:text-left tw:font-extrabold">
      {{ props.style.name }}
    </h2>

    <Separator />

    <CardDynamicImage
      class="tw:aspect-square"
      :src="props.style.image_url ?? undefined"
    />

    <p class="tw:text-left tw:text-sm">
      {{ props.style.description }}
    </p>

    <div
      v-if="selectedCard !== undefined && selectedCard?.id === props.style.id"
      class="tw:absolute tw:top-0 tw:left-0 tw:flex tw:h-full tw:w-full tw:flex-col tw:items-center tw:justify-center"
    >
      <CircleLoader class="tw:text-5xl tw:text-white" />
    </div>
  </CardBase>
</template>
