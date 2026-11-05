<script lang="ts" setup>
interface Props {
  imageSrc: string;
  selected?: boolean;
}
defineProps<Props>();

const emit = defineEmits<{
  select: [];
}>();
</script>

<template>
  <Card padding="sm" class="tw:border-2">
    <div class="tw:flex tw:items-center tw:justify-between">
      <img class="tw:mb-2 tw:w-[46px]" :src="imageSrc" />

      <div
        v-if="selected"
        class="tw:rounded tw:bg-success tw:px-2.5 tw:py-0.5 tw:text-white"
      >
        Selected
      </div>
    </div>

    <h2 class="tw:mb-2 tw:text-2xl tw:font-extrabold">
      <slot name="title" />
    </h2>

    <ChipList class="tw:mb-4">
      <slot name="tags" />
    </ChipList>

    <p class="tw:mb-8">
      <slot name="description" />
    </p>

    <Button
      size="md"
      variant="outlined"
      class="tw:w-full"
      @click="emit('select')"
    >
      {{ selected ? "Edit Bot" : "Select bot" }}
    </Button>
  </Card>
</template>
