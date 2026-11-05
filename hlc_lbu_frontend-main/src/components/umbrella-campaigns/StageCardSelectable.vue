<script setup lang="ts">
interface Stage {
  name: string;
  display_name: string;
}

interface Category {
  name: string;
  display_name: string;
  stages: Stage[];
}

const props = defineProps<{
  categories: Category[];
  modelValue?: string | null;
}>();

const emit = defineEmits(["update:modelValue"]);

const selectedCategory = ref<string | null>(props.modelValue ?? null);

watch(
  () => props.modelValue,
  (val) => {
    selectedCategory.value = val ?? null;
  },
);

function selectCategory(name: string) {
  selectedCategory.value = name;
  emit("update:modelValue", name);
}
</script>

<template>
  <div>
    <h2 class="tw:mb-6 tw:text-2xl tw:font-bold">
      {{ $t("umbrella-campaign.step-scene.stages.category-section") }}
    </h2>
    <div
      class="tw:grid tw:grid-cols-1 tw:gap-6 tw:sm:grid-cols-2 tw:md:grid-cols-3"
    >
      <button
        v-for="cat in categories"
        :key="cat.name"
        type="button"
        @click="selectCategory(cat.name)"
        class="tw:flex tw:cursor-pointer tw:flex-col tw:items-center tw:justify-center tw:rounded-xl tw:border-2 tw:bg-white tw:p-6 tw:text-center tw:shadow tw:transition"
        :class="
          selectedCategory === cat.name
            ? 'tw:border-primary tw:bg-primary/10'
            : 'tw:border-transparent tw:hover:border-primary'
        "
      >
        <span
          class="tw:block tw:text-center tw:text-lg tw:font-semibold tw:whitespace-pre-line"
          >{{ cat.display_name }}</span
        >
      </button>
    </div>
  </div>
</template>
