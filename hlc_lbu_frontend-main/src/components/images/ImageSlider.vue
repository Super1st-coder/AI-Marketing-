<script setup lang="ts">
const props = defineProps<{ images: string[] }>();

const itemRefs = useTemplateRef<HTMLButtonElement[]>("itemRefs");
const { currentItem, currentIndex, items } = useSliderRef(
  () => props.images,
  0,
  { refs: itemRefs },
);
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-4">
    <div
      class="tw:aspect-square tw:overflow-hidden tw:rounded-2xl tw:border tw:border-gray-300 tw:bg-gray-500"
    >
      <img
        v-if="currentItem"
        class="tw:h-full tw:w-full tw:object-contain"
        :src="currentItem"
      />
    </div>

    <div v-if="items.length > 1" class="tw:flex tw:gap-3 tw:overflow-x-auto">
      <button
        v-for="(image, index) in items"
        ref="itemRefs"
        class="tw:shrink-0 tw:overflow-hidden tw:rounded-2xl tw:border-2 tw:border-gray-300 tw:bg-gray-500"
        :class="{
          'tw:border-primary': index === currentIndex,
        }"
        type="button"
        @click="currentIndex = index"
      >
        <img :src="image" class="tw:h-20" />
      </button>
    </div>
  </div>
</template>
