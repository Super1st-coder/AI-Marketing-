<script setup lang="ts">
import { UmbrellaCampaignStoryStageItem } from "@/services/projects/UmbrellaCampaignsApi";

interface Props {
  stageItem: UmbrellaCampaignStoryStageItem;
  selected?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  toggle: [stageItem: UmbrellaCampaignStoryStageItem];
}>();

const handleToggle = () => {
  emit("toggle", props.stageItem);
};
</script>

<template>
  <CardBase
    class="tw:flex tw:cursor-pointer tw:items-center tw:gap-3 tw:px-3 tw:py-4 tw:transition-all tw:duration-200 tw:select-none"
    :class="['tw:hover:-translate-y-0.5 tw:hover:shadow-md']"
    @click="handleToggle"
    :color="selected ? 'success' : undefined"
    :borderWidth="2"
  >
    <button class="tw:shrink-0" type="button">
      <Icon icon="tabler:grip-vertical" class="tw:text-2xl" />
    </button>

    <FieldBaseCheckbox :checked="selected" color="success" />

    <span
      class="tw:truncate tw:text-base tw:font-semibold tw:text-primary-text"
    >
      {{ stageItem.display_name }}
    </span>
  </CardBase>
</template>
