<script setup lang="ts">
import { FunnelData } from "@/services/UtilsApi";

const props = defineProps<{
  funnel: FunnelData;
  name: string;
  imageSrc: string;
}>();

const { value: selectedFunnelId } = useField<number>(() => props.name);
</script>

<template>
  <CardBase
    class="tw:relative tw:p-5"
    :class="{
      'tw:cursor-pointer': funnel.active,
      'tw:opacity-75': !funnel.active,
    }"
    :hoverColor="!funnel.active ? undefined : 'primary'"
    :color="selectedFunnelId === funnel.id ? 'primary' : 'default'"
  >
    <img :src="imageSrc" class="tw:mb-2 tw:w-[46px]" />

    <h2 class="tw:mb-4 tw:text-2xl tw:font-extrabold">
      {{ $t(`funnels.${funnel.name}.title`) }}
    </h2>

    <p class="tw:text-sm">
      {{ $t(`funnels.${funnel.name}.description`) }}
    </p>

    <Chip v-if="!funnel.active" class="tw:absolute tw:top-5 tw:right-5">
      Soon
    </Chip>
  </CardBase>
</template>
