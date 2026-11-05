<script setup lang="ts">
const props = defineProps<{ name: string; label: string }>();

const { value } = useField<string | undefined>(() => props.name);
</script>

<template>
  <div class="tw:grow tw:basis-0">
    <FieldText
      :name="name"
      :label="label"
      placeholder="Image URL"
      class="tw:mb-3 tw:grow"
    />

    <div
      class="tw:flex tw:aspect-square tw:items-center tw:justify-center tw:rounded-[5px] tw:bg-[#DFDAEA]"
    >
      <img
        v-if="value"
        :src="value"
        class="tw:h-full tw:w-full tw:object-contain"
      />
    </div>
  </div>
</template>
