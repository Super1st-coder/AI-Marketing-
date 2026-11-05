<script setup lang="ts">
defineProps<{
  image?: ImageLibraryFile | string;
  isSaving?: boolean;
  readOnly?: boolean;
}>();

const emit = defineEmits<{
  add: [];
  delete: [];
}>();
</script>

<template>
  <CardBase
    v-if="isSaving"
    color="secondary"
    borderRadius="sm"
    class="tw:flex tw:aspect-square tw:items-center tw:justify-center"
  >
    <CircleLoaderDefault />
  </CardBase>
  <!-- With image -->
  <div
    v-else-if="image"
    class="tw:group tw:relative tw:aspect-square tw:overflow-hidden tw:rounded-[10px] tw:bg-gray-500"
  >
    <!-- Image -->
    <ImgFile :src="image" class="tw:h-full tw:w-full tw:object-contain" />

    <!-- Black overlay -->
    <div
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:bg-black/50 tw:opacity-0 tw:transition tw:group-hover:opacity-100"
    ></div>

    <!-- Delete button -->
    <div
      v-if="!readOnly"
      class="tw:pointer-events-none tw:absolute tw:inset-0 tw:flex tw:items-start tw:justify-end tw:p-3 tw:opacity-0 tw:transition tw:group-hover:opacity-100"
    >
      <button
        type="button"
        class="tw:pointer-events-auto tw:text-white"
        @click="emit('delete')"
      >
        <Icon icon="tabler:trash" class="tw:text-[20px]" />
      </button>
    </div>
  </div>
  <!-- Without image -->
  <button
    v-else
    type="button"
    class="tw:aspect-square tw:rounded-[10px] tw:border tw:border-gray-300 tw:bg-gray-200"
    @click="emit('add')"
  >
    <!-- Text -->
    <div class="tw:flex tw:items-center tw:justify-center tw:text-gray-600">
      <Icon icon="tabler:plus" class="tw:mr-2 tw:text-[20px]" />
      <span class="tw:font-medium"> Add Image </span>
    </div>
  </button>
</template>
